"""OpenJev (AlexWortega/openjev) client for fast decision scoring and 4-role classification.

Pure OpenJev implementation running locally in-process on Apple Silicon (MPS/CPU) or via OPENJEV_ENDPOINT.
Target Model: https://huggingface.co/AlexWortega/openjev
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field
import transformers

# Suppress optional CUDA kernel notice messages on Apple Silicon
warnings.filterwarnings("ignore", message=".*causal_conv1d.*")
warnings.filterwarnings("ignore", message=".*flash-linear-attention.*")
transformers.logging.set_verbosity_error()

load_dotenv()


# Real OpenJev model identifier on Hugging Face: https://huggingface.co/AlexWortega/openjev
OPENJEV_MODEL = "AlexWortega/openjev"
DEFAULT_OPENJEV_SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"

OPENJEV_ROLE_CRITERIA = {
    "ai_researcher": (
        "Novel Artificial Intelligence and Machine Learning research papers, deep learning theory, "
        "model architectures, mathematical algorithms, training loss formulations, benchmarks, and arXiv preprints"
    ),
    "ai_engineer": (
        "Practical AI engineering, software engineering, developer tooling, Python packages, "
        "APIs, SDKs, LLM frameworks, agent orchestration, runtime kernels, deployment, and GitHub repositories"
    ),
    "startup_innovations": (
        "Technology and AI startups, venture capital funding rounds, seed investments, "
        "incubators, accelerators, company launches, acquisitions, and commercial enterprise breakthroughs"
    ),
    "noise": (
        "General non-technical news, sports, gaming, celebrity gossip, personal lifestyle stories, "
        "unrelated physical retail products, pure non-tech politics, clickbait, or irrelevant noise"
    ),
}

ROLE_HYPOTHESES = {
    "ai_researcher": "This text is primarily discussing novel machine learning research, mathematical algorithms, deep learning theory, training techniques, model architectures, or academic papers.",
    "ai_engineer": "This text is primarily discussing practical software engineering, developer tooling, Python packages, APIs, SDKs, runtime deployment, or code implementation.",
    "startup_innovations": "This text is primarily discussing technology startups, venture capital funding rounds, seed investments, business acquisitions, or commercial innovation.",
    "noise": "This text is primarily discussing non-technical topics, lifestyle, sports, entertainment, physical consumer products, or irrelevant noise.",
}


class JevClassificationResult(BaseModel):
    """Structured decision output from OpenJev (AlexWortega/openjev) for 4 target roles."""

    primary_role: str = Field(
        description="The primary target role (ai_researcher, ai_engineer, startup_innovations, noise)"
    )
    confidence: float = Field(
        default=0.0, description="Confidence score for the primary choice (0.0 - 1.0)"
    )
    role_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probabilities across all 4 roles from OpenJev decision scoring",
    )
    researcher_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for AI / ML Researcher",
    )
    engineer_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for Software & AI Engineer",
    )
    startup_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for Startup & Innovations",
    )
    noise_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability for Noise / Irrelevant",
    )
    # Backward compatibility aliases
    ai_ml_score: float = Field(default=0.0)
    aiml_score: float = Field(default=0.0)
    irrelevant_score: float = Field(default=0.0)
    model: str = Field(
        default=OPENJEV_MODEL,
        description="Model identifier used for classification (AlexWortega/openjev)",
    )
    is_live_api: bool = Field(
        default=True,
        description="True for all live OpenJev model outputs",
    )
    raw_response: Optional[Dict[str, Any]] = None



import threading

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
        from pathlib import Path
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        subfolder = os.getenv("OPENJEV_SUBFOLDER", DEFAULT_OPENJEV_SUBFOLDER)
        _device = "mps" if torch.backends.mps.is_available() else "cpu"

        fine_tuned_path = Path(__file__).resolve().parent.parent.parent / "models" / "fine_tuned_openjev_4role"
        if fine_tuned_path.exists() and (fine_tuned_path / "adapter_config.json").exists():
            from peft import PeftModel
            print(f"Loading Fine-Tuned 4-Role LoRA Model from: {fine_tuned_path} on {_device.upper()}...")
            _tokenizer = AutoTokenizer.from_pretrained(str(fine_tuned_path), trust_remote_code=True)
            base_model = AutoModelForSequenceClassification.from_pretrained(
                OPENJEV_MODEL,
                subfolder=subfolder,
                num_labels=4,
                id2label={0: "ai_researcher", 1: "ai_engineer", 2: "startup_innovations", 3: "noise"},
                label2id={"ai_researcher": 0, "ai_engineer": 1, "startup_innovations": 2, "noise": 3},
                ignore_mismatched_sizes=True,
                trust_remote_code=True,
                dtype=torch.float32,
            )
            _model = PeftModel.from_pretrained(base_model, str(fine_tuned_path)).to(_device)
            _model.eval()
            _is_fine_tuned = True
            return _tokenizer, _model, _device, _is_fine_tuned

        try:
            _tokenizer = AutoTokenizer.from_pretrained(
                OPENJEV_MODEL,
                subfolder=subfolder,
                trust_remote_code=True,
            )
        except Exception:
            _tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B", trust_remote_code=True)
        _model = AutoModelForSequenceClassification.from_pretrained(
            OPENJEV_MODEL,
            subfolder=subfolder,
            trust_remote_code=True,
            dtype=torch.float32,
        ).to(_device)
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
                "criteria": OPENJEV_ROLE_CRITERIA,
            }
        },
    }


def _classify_locally(title: str, description: str, source: str) -> JevClassificationResult:
    """Execute in-process local inference using AlexWortega/openjev (or Fine-Tuned LoRA model) on Apple Silicon."""
    import torch

    tokenizer, model, device, is_fine_tuned = _get_local_model()

    premise = f"Based on this technical news summary: Title: {title.strip()}. Description: {description.strip()}. Source: {source.strip()}."
    role_keys = ["ai_researcher", "ai_engineer", "startup_innovations", "noise"]

    with _model_lock:
        if is_fine_tuned:
            # Ultra-fast 1-pass sequence classification with fine-tuned head
            inputs = tokenizer(
                premise,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits  # shape: (1, 4)
                probs = torch.softmax(logits, dim=-1)[0].cpu().tolist()

            role_probs = {
                role_keys[i]: round(float(probs[i]), 3)
                for i in range(len(role_keys))
            }
            raw_logits = logits[0].cpu().tolist()
        else:
            # 4-pass cross-encoder entailment evaluation with base OpenJev
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
                logits = outputs.logits  # shape: (4, num_labels)

                # Extract true entailment logit (label 1: 0=contradiction, 1=entailment, 2=neutral)
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
    startup_score = role_probs.get("startup_innovations", 0.0)
    noise_score = role_probs.get("noise", 0.0)
    ai_ml_score = max(researcher_score, engineer_score)

    primary_role = max(role_probs, key=role_probs.get) if role_probs else "ai_researcher"
    confidence = role_probs.get(primary_role, 0.0)

    return JevClassificationResult(
        primary_role=primary_role,
        confidence=confidence,
        role_probabilities=role_probs,
        researcher_score=researcher_score,
        engineer_score=engineer_score,
        startup_score=startup_score,
        noise_score=noise_score,
        ai_ml_score=ai_ml_score,
        aiml_score=ai_ml_score,
        irrelevant_score=noise_score,
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
                "criteria": OPENJEV_ROLE_CRITERIA,
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
            if r_key in OPENJEV_ROLE_CRITERIA:
                role_probs[r_key] = round(float(p), 3)
    elif "choice" in role_answer:
        chosen = role_answer["choice"]
        conf = float(role_answer.get("confidence", 0.85))
        rem = round((1.0 - conf) / 3.0, 3)
        for r in OPENJEV_ROLE_CRITERIA:
            role_probs[r] = conf if r == chosen else rem

    for role in ("ai_researcher", "ai_engineer", "startup_innovations", "noise"):
        if role not in role_probs:
            role_probs[role] = 0.0

    researcher_score = role_probs.get("ai_researcher", 0.0)
    engineer_score = role_probs.get("ai_engineer", 0.0)
    startup_score = role_probs.get("startup_innovations", 0.0)
    noise_score = role_probs.get("noise", 0.0)
    ai_ml_score = max(researcher_score, engineer_score)

    primary_role = max(role_probs, key=role_probs.get) if role_probs else "ai_researcher"
    confidence = role_probs.get(primary_role, 0.0)

    return JevClassificationResult(
        primary_role=primary_role,
        confidence=confidence,
        role_probabilities=role_probs,
        researcher_score=researcher_score,
        engineer_score=engineer_score,
        startup_score=startup_score,
        noise_score=noise_score,
        ai_ml_score=ai_ml_score,
        aiml_score=ai_ml_score,
        irrelevant_score=noise_score,
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
    """
    Classify a news item strictly using OpenJev (AlexWortega/openjev).
    
    If OPENJEV_ENDPOINT is set, uses the remote endpoint.
    Otherwise, runs directly in-process locally on Apple Silicon (MPS).
    """
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


