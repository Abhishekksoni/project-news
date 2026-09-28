"""LoRA Fine-Tuning for AlexWortega/openjev on Apple Silicon Metal GPU (mps).

Refactored for 3-Role Classification:
0: ai_researcher (🔬 AI & ML Research)
1: ai_engineer   (🧑‍💻 AI & Software Engineering)
2: noise         (🗑️ Noise / Irrelevant)

Features:
- Reproducible random seed (set_seed(42))
- Pinned tokenizer & model loading (no silent fallbacks)
- Explicit pad_token_id configuration
- Trainable-only parameters optimizer
- Exact ceiling step calculation with Cosine learning rate decay
- Best model checkpointing based on validation weighted F1
- Full per-class classification report & confusion matrix
- Unbiased final evaluation on held-out test.jsonl
"""

import functools
import json
import math
import os
import sys
import time
from pathlib import Path

# Add src to path for taxonomy
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, TaskType, get_peft_model
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    get_cosine_schedule_with_warmup,
    set_seed,
)

from classification.taxonomy import ID2LABEL, LABEL2ID, ROLE_DISPLAY_NAMES, ROLES

# 1. Configuration
MODEL_ID = "AlexWortega/openjev"
DEFAULT_SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"
OUTPUT_MODEL_DIR = "models/fine_tuned_openjev_3role"
NUM_LABELS = len(ROLES)


def collate_wrapper(batch, data_collator):
    return data_collator(batch)


def evaluate_model(model, val_loader, device, id2label, role_names):
    """Run evaluation and return (loss, weighted_f1, macro_f1, report_str, cm)."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in val_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            total_loss += loss.item() * len(batch["labels"])
            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1).cpu().tolist()
            all_preds.extend(preds)
            all_labels.extend(batch["labels"].cpu().tolist())

    n_samples = len(all_labels)
    avg_loss = total_loss / n_samples if n_samples else 0.0
    weighted_f1 = float(f1_score(all_labels, all_preds, average="weighted", zero_division=0))
    macro_f1 = float(f1_score(all_labels, all_preds, average="macro", zero_division=0))

    target_names = [role_names.get(id2label[i], id2label[i]) for i in range(len(id2label))]
    report_str = classification_report(
        all_labels,
        all_preds,
        labels=list(range(len(id2label))),
        target_names=target_names,
        digits=4,
        zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(id2label))))

    return avg_loss, weighted_f1, macro_f1, report_str, cm


def train_openjev():
    print("=" * 80)
    print(" 🚀 STARTING ROBUST 3-ROLE LoRA FINE-TUNING FOR AlexWortega/openjev")
    print("=" * 80)

    # 1. Set seed for complete reproducibility
    set_seed(42)

    # 2. Device Setup
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f" Target Compute Accelerator: {device.upper()}")

    # 3. Check Datasets
    train_path = "dataset/train.jsonl"
    val_path = "dataset/val.jsonl"
    test_path = "dataset/test.jsonl"
    if not os.path.exists(train_path) or not os.path.exists(val_path) or not os.path.exists(test_path):
        raise FileNotFoundError("Datasets not found! Please run `python scripts/build_dataset.py` first.")

    raw_datasets = load_dataset(
        "json",
        data_files={"train": train_path, "validation": val_path, "test": test_path},
    )
    print(
        f" Loaded Train Set: {len(raw_datasets['train'])} rows | "
        f"Val Set: {len(raw_datasets['validation'])} rows | "
        f"Held-Out Test Set: {len(raw_datasets['test'])} rows"
    )

    # 4. Load Tokenizer with strict error handling (no silent swaps)
    subfolder = os.getenv("OPENJEV_SUBFOLDER", DEFAULT_SUBFOLDER)
    print(f" Loading Tokenizer for {MODEL_ID} (subfolder: {subfolder})...")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        subfolder=subfolder,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 5. Tokenize Dataset
    def preprocess_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=256)

    tokenized_datasets = raw_datasets.map(
        preprocess_function,
        batched=True,
        remove_columns=["id", "text", "label_name"],
    )
    tokenized_datasets = tokenized_datasets.rename_column("label", "labels")
    tokenized_datasets.set_format("torch")

    # 6. Base Model Loading
    print(f" Loading Base Model: {MODEL_ID} with {NUM_LABELS} Output Classes...")
    base_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        subfolder=subfolder,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=True,
        dtype=torch.float32,
    )
    base_model.config.pad_token_id = tokenizer.pad_token_id

    # 7. LoRA Configuration
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
        modules_to_save=["score"],
    )
    model = get_peft_model(base_model, lora_config)
    model.to(device)

    print("\n Trainable Parameter Summary:")
    model.print_trainable_parameters()

    # 8. DataLoaders
    batch_size = 2
    grad_accum_steps = 4
    epochs = 3
    lr = 2e-4

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8)
    collate_fn = functools.partial(collate_wrapper, data_collator=data_collator)

    train_loader = DataLoader(
        tokenized_datasets["train"],
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn,
    )
    val_loader = DataLoader(
        tokenized_datasets["validation"],
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
    )
    test_loader = DataLoader(
        tokenized_datasets["test"],
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
    )

    # 9. Optimizer & Scheduler (trainable parameters only)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=0.01)

    total_update_steps = math.ceil(len(train_loader) / grad_accum_steps) * epochs
    warmup_steps = int(0.1 * total_update_steps)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_update_steps,
    )

    print(f"\n Training Config:")
    print(f"   Epochs:                     {epochs}")
    print(f"   Batch Size (Micro):         {batch_size}")
    print(f"   Gradient Accumulation:      {grad_accum_steps} (Effective Batch Size = {batch_size * grad_accum_steps})")
    print(f"   Total Optimizer Steps:      {total_update_steps} (Warmup = {warmup_steps})")
    print(f"   Learning Rate:              {lr} (Cosine decay)\n")

    # 10. Training Loop with Checkpointing
    best_val_f1 = -1.0
    best_epoch = 0
    os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        total_train_loss = 0.0
        start_time = time.time()
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss / grad_accum_steps
            loss.backward()
            total_train_loss += loss.item() * grad_accum_steps

            if step % grad_accum_steps == 0 or step == len(train_loader):
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            if step % 40 == 0 or step == len(train_loader):
                print(
                    f"   [Epoch {epoch}/{epochs} | Step {step:3d}/{len(train_loader)}] "
                    f"Batch Loss: {loss.item() * grad_accum_steps:.4f} | LR: {scheduler.get_last_lr()[0]:.2e}"
                )

        avg_train_loss = total_train_loss / len(train_loader)
        val_loss, val_wf1, val_mf1, val_report, val_cm = evaluate_model(
            model, val_loader, device, ID2LABEL, ROLE_DISPLAY_NAMES
        )
        elapsed = time.time() - start_time

        print(f"\n{'='*70}")
        print(f" 📊 EPOCH {epoch}/{epochs} SUMMARY (Time: {elapsed:.1f}s)")
        print(f"    Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f}")
        print(f"    Val Weighted F1: {val_wf1:.4f} | Val Macro F1: {val_mf1:.4f}")
        print(f"\n 📋 VALIDATION CLASSIFICATION REPORT:")
        print(val_report)
        print(" 🔢 CONFUSION MATRIX (Rows: Actual, Cols: Predicted):")
        print(f"    Labels: {[ID2LABEL[i] for i in range(NUM_LABELS)]}")
        for r_idx, row in enumerate(val_cm):
            print(f"    {ID2LABEL[r_idx]:15s}: {row}")
        print(f"{'='*70}\n")

        # Save Best Model Checkpoint
        if val_wf1 > best_val_f1:
            best_val_f1 = val_wf1
            best_epoch = epoch
            print(f" 🌟 NEW BEST MODEL! (Weighted F1: {val_wf1:.4f}). Saving checkpoint to {OUTPUT_MODEL_DIR}...")
            model.save_pretrained(OUTPUT_MODEL_DIR)
            tokenizer.save_pretrained(OUTPUT_MODEL_DIR)

            # Save training metadata
            meta = {
                "base_model": MODEL_ID,
                "subfolder": subfolder,
                "num_labels": NUM_LABELS,
                "roles": ROLES,
                "id2label": ID2LABEL,
                "label2id": LABEL2ID,
                "best_epoch": best_epoch,
                "val_loss": val_loss,
                "val_weighted_f1": val_wf1,
                "val_macro_f1": val_mf1,
            }
            with open(os.path.join(OUTPUT_MODEL_DIR, "model_meta.json"), "w") as f:
                json.dump(meta, f, indent=2)

    # 11. Final Evaluation on Held-Out Test Set (Untouched during training)
    print("\n" + "=" * 80)
    print(" 🏁 FINAL EVALUATION ON UNTOUCHED HELD-OUT TEST SET (test.jsonl)")
    print("=" * 80)

    # Load best checkpoint weights
    print(f" Loading best checkpoint from Epoch {best_epoch} ({OUTPUT_MODEL_DIR})...")
    best_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        subfolder=subfolder,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=True,
        dtype=torch.float32,
    )
    best_model.config.pad_token_id = tokenizer.pad_token_id
    eval_model = PeftModel.from_pretrained(best_model, OUTPUT_MODEL_DIR).to(device)

    test_loss, test_wf1, test_mf1, test_report, test_cm = evaluate_model(
        eval_model, test_loader, device, ID2LABEL, ROLE_DISPLAY_NAMES
    )

    print(f"\n 🏆 FINAL HELD-OUT TEST METRICS:")
    print(f"    Test Loss:        {test_loss:.4f}")
    print(f"    Test Weighted F1: {test_wf1:.4f}")
    print(f"    Test Macro F1:    {test_mf1:.4f}")
    print(f"\n 📋 TEST CLASSIFICATION REPORT:")
    print(test_report)
    print(" 🔢 TEST CONFUSION MATRIX (Rows: Actual, Cols: Predicted):")
    for r_idx, row in enumerate(test_cm):
        print(f"    {ID2LABEL[r_idx]:15s}: {row}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    train_openjev()
