"""Jev AI / OpenJev client for fast decision scoring and 3-role classification using hosted inference."""

import os
from typing import Any
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field

load_dotenv()

HF_ROUTER_ENDPOINT = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
CUSTOM_OPENJEV_ENDPOINT = "https://router.huggingface.co/hf-inference/models/openjev/openjev"

LABEL_MAPPING = {
    "AI/ML Research: research papers, novel ML methods, model architectures, "
    "training techniques, datasets, benchmarks, evaluations, mathematical theory "
    "and fundamental advances in machine learning": "ai_researcher",

    "AI Engineering/Software Development: practical implementation of AI systems, "
    "LLM applications, APIs, SDKs, agents, RAG, inference, developer tools, "
    "frameworks, databases, infrastructure, deployment, performance, open-source "
    "software and production AI engineering": "ai_engineer",

    "Startup/Innovation: AI or technology startups, venture funding, acquisitions, "
    "incubators, accelerators, company launches, major product launches, "
    "commercialization, enterprise adoption, business models, partnerships and "
    "emerging technologies with significant commercial potential": "startup_innovation",

    "Irrelevant / Non-Technical / Noise: general news, sports, gaming, celebrity gossip, "
    "personal lifestyle stories, unrelated physical products, pure non-tech politics, "
    "clickbait, or content not relevant to AI, software engineering, or tech startups": "irrelevant",
}


class JevClassificationResult(BaseModel):
    """Structured decision output from Jev / OpenJev AI."""

    primary_role: str = Field(
        description="The primary target role (ai_researcher, ai_engineer, startup_innovation, irrelevant)"
    )
    confidence: float = Field(
        default=0.0, description="Confidence score for the primary choice (0.0 - 1.0)"
    )
    role_probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Probabilities across all 4 roles from choice question",
    )
    researcher_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability of high relevance for AI/ML Researcher",
    )
    engineer_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability of high relevance for AI Engineer / Developer",
    )
    startup_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability of high relevance for Startup & Innovation (big/emerging)",
    )
    irrelevant_score: float = Field(
        default=0.0,
        description="0.0 - 1.0 probability of article being irrelevant / non-tech noise",
    )
    is_live_api: bool = Field(
        default=False,
        description="True if result came from live API; False if simulated mock",
    )
    raw_response: dict[str, Any] | None = None


def build_jev_request(title: str, description: str, source: str) -> dict[str, Any]:
    """Construct the decision question payload."""
    inputs_text = f"Title: {title}. Description: {description}. Source: {source}"
    return {
        "inputs": inputs_text,
        "parameters": {
            "candidate_labels": list(LABEL_MAPPING.keys()),
        },
    }


def classify_with_jev(
    title: str,
    description: str,
    source: str,
    api_key: str | None = None,
    timeout: float = 15.0,
) -> JevClassificationResult:
    """
    Classify a news item using hosted Hugging Face zero-shot decision model or OpenJev.
    Supports HF_TOKEN / HUGGINGFACE_API_KEY / JEV_API_KEY.
    """
    token = (
        api_key
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("JEV_API_KEY")
    )

    if not token:
        return _simulate_jev_classification(title, description, source)

    endpoint = os.getenv("OPENJEV_ENDPOINT", HF_ROUTER_ENDPOINT)
    payload = build_jev_request(title, description, source)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            role_probs: dict[str, float] = {}

            if isinstance(data, list):
                for item in data:
                    lbl = item.get("label")
                    scr = float(item.get("score", 0.0))
                    role_key = LABEL_MAPPING.get(lbl, "ai_engineer")
                    role_probs[role_key] = round(scr, 3)
            elif isinstance(data, dict):
                labels = data.get("labels", [])
                scores = data.get("scores", [])
                for lbl, scr in zip(labels, scores):
                    role_key = LABEL_MAPPING.get(lbl, "ai_engineer")
                    role_probs[role_key] = round(float(scr), 3)

            r_score = role_probs.get("ai_researcher", 0.0)
            e_score = role_probs.get("ai_engineer", 0.0)
            s_score = role_probs.get("startup_innovation", 0.0)
            i_score = role_probs.get("irrelevant", 0.0)

            primary_role = (
                max(role_probs, key=role_probs.get) if role_probs else "ai_engineer"
            )
            confidence = role_probs.get(primary_role, 0.0)

            return JevClassificationResult(
                primary_role=primary_role,
                confidence=confidence,
                role_probabilities=role_probs,
                researcher_score=r_score,
                engineer_score=e_score,
                startup_score=s_score,
                irrelevant_score=i_score,
                is_live_api=True,
                raw_response=data if isinstance(data, dict) else {"results": data},
            )
    except Exception as e:
        print(f"[OpenJev / HF API Notice] ({e}), using test simulation mode.")
        return _simulate_jev_classification(title, description, source)


def _simulate_jev_classification(
    title: str, description: str, source: str
) -> JevClassificationResult:
    """Heuristic simulation of Jev non-autoregressive scoring for testing without live API keys."""
    text = f"{title} {description} {source}".lower()

    # Irrelevant signals
    irr_keywords = [
        "earth is tearing apart", "catastrophe", "museum of art", "quotes",
        "human connection", "anxious generation", "breaking up with google play",
        "restless ghosts", "roman world", "studying latin", "latin rigorously",
        "plunging test scores", "viral giants clip", "husband", "mom in that", "parenting",
        "relationship", "sports", "celebrity", "dating", "lifestyle"
    ]
    i_matches = sum(1 for w in irr_keywords if w in text)
    i_score = max(0.04, 0.05 + (i_matches * 0.35))

    # Researcher signals
    research_words = [
        "arxiv",
        "alphaxiv",
        "bair",
        "paper",
        "theorem",
        "loss",
        "dataset",
        "benchmark",
        "parameter",
        "latent",
        "math",
        "architecture",
        "attention",
        "transformer",
    ]
    r_matches = sum(1 for w in research_words if w in text)
    r_score = min(0.98, max(0.05, 0.2 + (r_matches * 0.15)))

    # Engineer signals
    engineer_words = [
        "api",
        "wrapper",
        "llm",
        "library",
        "code",
        "python",
        "software",
        "agent",
        "os",
        "git",
        "hugging face",
        "framework",
        "database",
        "latency",
        "vision model",
        "context engineering",
        "tokenmaxxing",
        "nixos",
        "simd",
    ]
    e_matches = sum(1 for w in engineer_words if w in text)
    e_score = min(0.98, max(0.05, 0.25 + (e_matches * 0.14)))

    # Startup & Innovation signals
    startup_words = [
        "startup",
        "iit",
        "incubation",
        "raise",
        "million",
        "fund",
        "venture",
        "market",
        "partner",
        "launch",
        "program",
        "innovation",
        "commercial",
        "enterprise",
        "yourstory",
    ]
    s_matches = sum(1 for w in startup_words if w in text)
    s_score = min(0.98, max(0.05, 0.15 + (s_matches * 0.16)))

    total = r_score + e_score + s_score + i_score
    probs = {
        "ai_researcher": round(r_score / total, 3),
        "ai_engineer": round(e_score / total, 3),
        "startup_innovation": round(s_score / total, 3),
        "irrelevant": round(i_score / total, 3),
    }

    primary = max(probs, key=probs.get)
    confidence = round(probs[primary], 2)

    return JevClassificationResult(
        primary_role=primary,
        confidence=confidence,
        role_probabilities=probs,
        researcher_score=round(r_score, 3),
        engineer_score=round(e_score, 3),
        startup_score=round(s_score, 3),
        irrelevant_score=round(i_score, 3),
        is_live_api=False,
    )
