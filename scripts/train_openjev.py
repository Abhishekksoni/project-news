"""Robust LoRA Fine-Tuning Script for AlexWortega/openjev across 4 Target Roles on Apple Silicon MPS / CUDA."""

import os
import shutil
import time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_cosine_schedule_with_warmup,
)
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from sklearn.metrics import accuracy_score, f1_score

MODEL_ID = "AlexWortega/openjev"
DEFAULT_SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"
OUTPUT_MODEL_DIR = "./models/fine_tuned_openjev_4role"

ID2LABEL = {
    0: "ai_researcher",
    1: "ai_engineer",
    2: "startup_innovations",
    3: "noise",
}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}


def collate_fn(batch, pad_token_id: int):
    """Custom fast collation with dynamic padding for torch tensors."""
    max_len = max(len(item["input_ids"]) for item in batch)
    input_ids = []
    attention_masks = []
    labels = []

    for item in batch:
        seq_len = len(item["input_ids"])
        pad_len = max_len - seq_len
        input_ids.append(item["input_ids"] + [pad_token_id] * pad_len)
        attention_masks.append(item["attention_mask"] + [0] * pad_len)
        labels.append(item["labels"])

    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_masks, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def evaluate_model(model, dataloader, device):
    """Evaluate accuracy and weighted F1 on validation set."""
    model.eval()
    all_preds = []
    all_labels = []
    total_loss = 0.0

    with torch.no_grad():
        for batch in dataloader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            total_loss += loss.item() * len(batch["labels"])
            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(batch["labels"].cpu().numpy())

    avg_loss = total_loss / len(all_labels) if all_labels else 0.0
    acc = float(accuracy_score(all_labels, all_preds))
    f1 = float(f1_score(all_labels, all_preds, average="weighted"))
    return avg_loss, acc, f1


def train_openjev():
    print("=" * 80)
    print(" 🚀 STARTING 4-ROLE LoRA FINE-TUNING FOR AlexWortega/openjev")
    print("=" * 80)

    # 1. Device Setup
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f" Target Compute Accelerator: {device.upper()}")
    os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

    # 2. Check Datasets
    train_path = "dataset/train.jsonl"
    val_path = "dataset/val.jsonl"
    if not os.path.exists(train_path) or not os.path.exists(val_path):
        raise FileNotFoundError("Datasets not found! Please run `python scripts/build_dataset.py` first.")

    raw_datasets = load_dataset("json", data_files={"train": train_path, "validation": val_path})
    print(f" Loaded Train Set: {len(raw_datasets['train'])} rows | Val Set: {len(raw_datasets['validation'])} rows")

    # 3. Tokenizer
    subfolder = os.getenv("OPENJEV_SUBFOLDER", DEFAULT_SUBFOLDER)
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            subfolder=subfolder,
            trust_remote_code=True,
        )
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B", trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4. Tokenization Function (max 256 tokens)
    def tokenize(examples):
        tokens = tokenizer(examples["text"], truncation=True, max_length=256)
        tokens["labels"] = examples["label"]
        return tokens

    train_encoded = raw_datasets["train"].map(tokenize, batched=True, remove_columns=raw_datasets["train"].column_names)
    val_encoded = raw_datasets["validation"].map(tokenize, batched=True, remove_columns=raw_datasets["validation"].column_names)

    pad_id = tokenizer.pad_token_id or 0
    train_loader = DataLoader(
        train_encoded,
        batch_size=2,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_id),
    )
    val_loader = DataLoader(
        val_encoded,
        batch_size=4,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, pad_id),
    )

    # 5. Model Loading & LoRA Configuration
    print(f" Loading base model weights: {MODEL_ID} ({subfolder})...")
    base_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        subfolder=subfolder,
        num_labels=4,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=True,
        dtype=torch.float32,
    )

    peft_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(base_model, peft_config).to(device)
    model.print_trainable_parameters()

    # 6. Training Hyperparameters
    epochs = 3
    grad_accum_steps = 4
    lr = 3e-4
    total_steps = (len(train_loader) // grad_accum_steps) * epochs
    warmup_steps = int(total_steps * 0.1)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    lr_scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    # Initial zero-shot evaluation baseline
    print("\n Evaluating pre-training baseline on validation set...")
    base_loss, base_acc, base_f1 = evaluate_model(model, val_loader, device)
    print(f" Baseline Validation -> Loss: {base_loss:.4f} | Accuracy: {base_acc * 100:.2f}% | F1: {base_f1:.4f}\n")

    # 7. Training Loop
    print(f" Beginning LoRA fine-tuning for {epochs} epochs ({total_steps} optimizer steps)...")
    start_time = time.time()
    global_step = 0
    best_acc = 0.0

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        step_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss / grad_accum_steps
            loss.backward()

            step_loss += loss.item() * grad_accum_steps
            epoch_loss += loss.item() * grad_accum_steps

            if step % grad_accum_steps == 0 or step == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 10 == 0 or global_step == total_steps:
                    curr_lr = lr_scheduler.get_last_lr()[0]
                    print(f" [Epoch {epoch}/{epochs} | Step {global_step}/{total_steps}] Loss: {step_loss / grad_accum_steps:.4f} | LR: {curr_lr:.2e}")
                step_loss = 0.0

        # Epoch Validation
        val_loss, val_acc, val_f1 = evaluate_model(model, val_loader, device)
        print(f"\n ⭐ [Epoch {epoch}/{epochs} SUMMARY] Val Loss: {val_loss:.4f} | Val Accuracy: {val_acc * 100:.2f}% | Weighted F1: {val_f1:.4f}\n")

        if val_acc > best_acc:
            best_acc = val_acc

    total_time = time.time() - start_time
    print("=" * 80)
    print(f" 🎉 TRAINING COMPLETE in {total_time / 60:.2f} minutes!")
    print(f" Final Validation Accuracy: {val_acc * 100:.2f}% (Best: {best_acc * 100:.2f}%)")
    print(f" Final Validation Weighted F1: {val_f1:.4f}")
    print("=" * 80)

    # 8. Save Model and Tokenizer
    output_dir = Path(OUTPUT_MODEL_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"\n ✅ Fine-tuned model adapter saved to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    train_openjev()
