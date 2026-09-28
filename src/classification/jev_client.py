"""OpenJev (AlexWortega/openjev) client for fast decision scoring and 3-role classification.

Pure OpenJev implementation running locally in-process on Apple Silicon (MPS/CPU) or via OPENJEV_ENDPOINT.
Target Model: https://huggingface.co/AlexWortega/openjev
"""

from __future__ import annotations

import os
import threading
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field
import transformers

from classification.taxonomy import (
    ID2LABEL,
    LABEL2ID,
    ROLE_CRITERIA,
    ROLE_DISPLAY_NAMES,
    ROLE_HYPOTHESES,
    ROLES,
)

# Suppress optional CUDA kernel notice messages on Apple Silicon
warnings.filterwarnings("ignore", message=".*causal_conv1d.*")
warnings.filterwarnings("ignore", message=".*flash-linear-attention.*")
transformers.logging.set_verbosity_error()

load_dotenv()

OPENJEV_MODEL = "AlexWortega/openjev"
DEFAULT_OPENJEV_SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"


class JevClassificationResult(BaseModel):
    """Structured decision output from OpenJev (AlexWortega/openjev) for 3 target roles."""

    primary_role: str = Field(
        description="The primary target role (ai_researcher, ai_engineer, noise)"
    )
    confidence: float = Field(
        default=0.0, description="Confidence score for the primary choice (0.0 - 1.0)"
    )
    role_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probabilities across 3 roles from OpenJev decision scoring",
    )
    researcher_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for AI / ML Researcher",
    )
    engineer_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for Software & AI Engineer",
    )
    noise_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for Noise / Irrelevant",
    )
    # Backward compatibility aliases
    irrelevant_score: float = Field(default=0.0)
    startup_score: float = Field(default=0.0)
    ai_ml_score: float = Field(default=0.0)
    aiml_score: float = Field(default=0.0)
    model: str = Field(
        default=OPENJEV_MODEL,
        description="Model identifier used for classification (AlexWortega/openjev)",
    )
    is_live_api: bool = Field(
        default=True,
        description="True for all live OpenJev model outputs",
    )
    raw_response: Optional[Dict[str, Any]] = None


# Global in-process singleton cache for local execution
_tokenizer = None
_model = None
_device = None
_is_fine_tuned = False
_model_lock = threading.Lock()


def _get_local_model():
    """Lazily load and cache the local AlexWortega/openjev or fine-tuned model on MPS/CPU with thread safety."""
    global _tokenizer, _model, _device, _is_fine_tuned
    with _model_lock:
        if _model is not None:
            return _tokenizer, _model, _device, _is_fine_tuned

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        subfolder = os.getenv("OPENJEV_SUBFOLDER", DEFAULT_OPENJEV_SUBFOLDER)
        _device = "mps" if torch.backends.mps.is_available() else "cpu"

        # Check for 3-role fine-tuned adapter first
        fine_tuned_path = Path(__file__).resolve().parent.parent.parent / "models" / "fine_tuned_openjev_3role"
        if not fine_tuned_path.exists() or not (fine_tuned_path / "adapter_config.json").exists():
            # Fallback to existing fine-tuned path if 3role not yet created
            fine_tuned_path = Path(__file__).resolve().parent.parent.parent / "models" / "fine_tuned_openjev_4role"

        if fine_tuned_path.exists() and (fine_tuned_path / "adapter_config.json").exists():
            from peft import PeftModel

            print(f"Loading Fine-Tuned LoRA Model from: {fine_tuned_path} on {_device.upper()}...")
            _tokenizer = AutoTokenizer.from_pretrained(str(fine_tuned_path), trust_remote_code=True)
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token

            num_labels = len(ROLES)
            base_model = AutoModelForSequenceClassification.from_pretrained(
                OPENJEV_MODEL,
                subfolder=subfolder,
                num_labels=num_labels,
                id2label=ID2LABEL,
                label2id=LABEL2ID,
                ignore_mismatched_sizes=True,
                trust_remote_code=True,
                dtype=torch.float32,
            )
            base_model.config.pad_token_id = _tokenizer.pad_token_id
            _model = PeftModel.from_pretrained(base_model, str(fine_tuned_path)).to(_device)
            _model.eval()
            _is_fine_tuned = True
            return _tokenizer, _model, _device, _is_fine_tuned

        # Load base model directly without silent fallback
        _tokenizer = AutoTokenizer.from_pretrained(
            OPENJEV_MODEL,
            subfolder=subfolder,
            trust_remote_code=True,
        )
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token

        _model = AutoModelForSequenceClassification.from_pretrained(
            OPENJEV_MODEL,
            subfolder=subfolder,
            trust_remote_code=True,
            dtype=torch.float32,
        ).to(_device)
        _model.config.pad_token_id = _tokenizer.pad_token_id
        _model.eval()
        _is_fine_tuned = False

        return _tokenizer, _model, _device, _is_fine_tuned


def build_openjev_systemone_payload(
    title: str, description: str, source: str
) -> Dict[str, Any]:
    """Construct OpenJev System 1 payload structure."""
    state_context = f"Title: {title.strip()}\nDescription: {description.strip()}\nSource: {source.strip()}"
    return {
        "model": OPENJEV_MODEL,
        "state": state_context,
        "questions": {
            "role": {
                "type": "choice",
                "instructions": "Evaluate the article and determine which audience role benefits most.",
                "criteria": ROLE_CRITERIA,
            }
        },
    }


def _classify_locally(title: str, description: str, source: str) -> JevClassificationResult:
    """Execute in-process local inference using AlexWortega/openjev (or Fine-Tuned LoRA model) on Apple Silicon."""
    import torch

    tokenizer, model, device, is_fine_tuned = _get_local_model()

    premise = f"Based on this technical news summary: Title: {title.strip()}. Description: {description.strip()}. Source: {source.strip()}."
    role_keys = list(ROLES)

    with _model_lock:
        if is_fine_tuned:
            # Fast 1-pass sequence classification with fine-tuned head
            inputs = tokenizer(
                premise,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits  # shape: (1, num_labels)
                probs = torch.softmax(logits, dim=-1)[0].cpu().tolist()

            role_probs = {
                role_keys[i]: round(float(probs[i]), 3)
                for i in range(min(len(role_keys), len(probs)))
            }
            raw_logits = logits[0].cpu().tolist()
        else:
            # Cross-encoder entailment evaluation with base OpenJev NLI head
            hypotheses = [ROLE_HYPOTHESES[r] for r in role_keys]
            premises = [premise] * len(role_keys)

            inputs = tokenizer(
                premises,
                hypotheses,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits

                # Entailment index (label 1: 0=contradiction, 1=entailment, 2=neutral)
                entailment_idx = 1
                if hasattr(model.config, "label2id") and "entailment" in model.config.label2id:
                    entailment_idx = model.config.label2id["entailment"]

                entailment_logits = logits[:, entailment_idx]
                role_dist = torch.softmax(entailment_logits, dim=0).cpu().tolist()

            role_probs = {
                role_keys[i]: round(float(role_dist[i]), 3)
                for i in range(len(role_keys))
            }
            raw_logits = entailment_logits.cpu().tolist()

    researcher_score = role_probs.get("ai_researcher", 0.0)
    engineer_score = role_probs.get("ai_engineer", 0.0)
    noise_score = role_probs.get("noise", 0.0)
    ai_ml_score = max(researcher_score, engineer_score)

    primary_role = max(role_probs, key=role_probs.get) if role_probs else "ai_engineer"
    confidence = role_probs.get(primary_role, 0.0)

    return JevClassificationResult(
        primary_role=primary_role,
        confidence=confidence,
        role_probabilities=role_probs,
        researcher_score=researcher_score,
        engineer_score=engineer_score,
        noise_score=noise_score,
        irrelevant_score=noise_score,
        ai_ml_score=ai_ml_score,
        aiml_score=ai_ml_score,
        startup_score=0.0,
        model=OPENJEV_MODEL,
        is_live_api=True,
        raw_response={"role_logits": raw_logits},
    )


def _classify_via_endpoint(
    endpoint: str,
    title: str,
    description: str,
    source: str,
    api_key: str | None = None,
    timeout: float = 25.0,
) -> JevClassificationResult:
    """Execute remote HTTP inference if OPENJEV_ENDPOINT is configured."""
    token = (
        api_key
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("JEV_API_KEY")
    )
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    state_context = f"Title: {title.strip()}\nDescription: {description.strip()}\nSource: {source.strip()}"
    payload = {
        "model": OPENJEV_MODEL,
        "state": state_context,
        "questions": {
            "role": {
                "type": "choice",
                "instructions": "Evaluate the article and determine which audience role benefits most.",
                "criteria": ROLE_CRITERIA,
            }
        },
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    role_probs: Dict[str, float] = {}
    answers = data.get("answers", {})
    role_answer = answers.get("role", {}) or data.get("role", {})

    if "probabilities" in role_answer:
        for r_key, p in role_answer["probabilities"].items():
            if r_key in ROLE_CRITERIA:
                role_probs[r_key] = round(float(p), 3)
    elif "choice" in role_answer:
        chosen = role_answer["choice"]
        conf = float(role_answer.get("confidence", 0.85))
        rem = round((1.0 - conf) / 2.0, 3)
        for r in ROLE_CRITERIA:
            role_probs[r] = conf if r == chosen else rem

    for role in ROLES:
        if role not in role_probs:
            role_probs[role] = 0.0

    researcher_score = role_probs.get("ai_researcher", 0.0)
    engineer_score = role_probs.get("ai_engineer", 0.0)
    noise_score = role_probs.get("noise", 0.0)
    ai_ml_score = max(researcher_score, engineer_score)

    primary_role = max(role_probs, key=role_probs.get) if role_probs else "ai_engineer"
    confidence = role_probs.get(primary_role, 0.0)

    return JevClassificationResult(
        primary_role=primary_role,
        confidence=confidence,
        role_probabilities=role_probs,
        researcher_score=researcher_score,
        engineer_score=engineer_score,
        noise_score=noise_score,
        irrelevant_score=noise_score,
        ai_ml_score=ai_ml_score,
        aiml_score=ai_ml_score,
        startup_score=0.0,
        model=OPENJEV_MODEL,
        is_live_api=True,
        raw_response=data if isinstance(data, dict) else {"results": data},
    )


def classify_with_jev(
    title: str,
    description: str,
    source: str,
    api_key: str | None = None,
    timeout: float = 25.0,
) -> JevClassificationResult:
    """Classify a news item strictly using OpenJev (AlexWortega/openjev)."""
    endpoint = os.getenv("OPENJEV_ENDPOINT")
    if endpoint and endpoint.strip():
        return _classify_via_endpoint(
            endpoint=endpoint,
            title=title,
            description=description,
            source=source,
            api_key=api_key,
            timeout=timeout,
        )

    # Run directly in-process locally
    return _classify_locally(title, description, source)


