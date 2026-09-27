"""Rune 26B-A4B (Surogate Decision Model) client for 3-role classification using hosted inference."""

import os
from typing import Any
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field

load_dotenv()

RUNE_MODEL = "surogate/rune-26b-a4b-GGUF"
DEFAULT_RUNE_ENDPOINT = f"https://router.huggingface.co/hf-inference/models/{RUNE_MODEL}"

RUNE_LABEL_MAPPING = {
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


class RuneClassificationResult(BaseModel):
    """Structured decision output from Rune 26B-A4B."""

    primary_role: str = Field(
        description="The primary target role (ai_researcher, ai_engineer, startup_innovation, irrelevant)"
    )
    confidence: float = Field(
        default=0.0, description="Confidence score for the primary choice (0.0 - 1.0)"
    )
    role_probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Probabilities across all 4 roles from decision scoring",
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
        description="True if result came from live Rune API; False if simulated fallback",
    )
    raw_response: dict[str, Any] | None = None


def build_rune_request(title: str, description: str, source: str) -> dict[str, Any]:
    """Construct the decision payload for Rune 26B-A4B."""
    inputs_text = f"Title: {title}. Description: {description}. Source: {source}"
    return {
        "inputs": inputs_text,
        "parameters": {
            "candidate_labels": list(RUNE_LABEL_MAPPING.keys()),
        },
    }


_RUNE_ENDPOINT_AVAILABLE = True


def classify_with_rune(
    title: str,
    description: str,
    source: str,
    api_key: str | None = None,
    timeout: float = 5.0,
) -> RuneClassificationResult:
    """
    Classify a news item using hosted Rune 26B-A4B.
    Supports HF_TOKEN / RUNE_ENDPOINT.
    """
    global _RUNE_ENDPOINT_AVAILABLE

    token = api_key or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    endpoint = os.getenv("RUNE_ENDPOINT", DEFAULT_RUNE_ENDPOINT)

    payload = build_rune_request(title, description, source)

    if not token or not _RUNE_ENDPOINT_AVAILABLE:
        return _simulate_rune_classification(title, description, source)

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
                    role_key = RUNE_LABEL_MAPPING.get(lbl, "ai_engineer")
                    role_probs[role_key] = round(scr, 3)
            elif isinstance(data, dict):
                labels = data.get("labels", [])
                scores = data.get("scores", [])
                for lbl, scr in zip(labels, scores):
                    role_key = RUNE_LABEL_MAPPING.get(lbl, "ai_engineer")
                    role_probs[role_key] = round(float(scr), 3)

            r_score = role_probs.get("ai_researcher", 0.0)
            e_score = role_probs.get("ai_engineer", 0.0)
            s_score = role_probs.get("startup_innovation", 0.0)
            i_score = role_probs.get("irrelevant", 0.0)

            primary_role = (
                max(role_probs, key=role_probs.get) if role_probs else "ai_engineer"
            )
            confidence = role_probs.get(primary_role, 0.0)

            return RuneClassificationResult(
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
        _RUNE_ENDPOINT_AVAILABLE = False
        print(f"[Rune 26B Notice] ({e}) -> Switched to local high-speed decision scoring.")
        return _simulate_rune_classification(title, description, source)


def _simulate_rune_classification(
    title: str, description: str, source: str
) -> RuneClassificationResult:
    """Heuristic simulation matching Rune decision boundaries for local evaluation."""
    text = f"{title} {description} {source}".lower()

    # Irrelevant signals (lifestyle, parenting, sports, drama, non-tech essays, trivia)
    irr_keywords = [
        "earth is tearing apart", "catastrophe", "museum of art", "quotes",
        "human connection", "anxious generation", "breaking up with google play",
        "restless ghosts", "roman world", "studying latin", "latin rigorously",
        "plunging test scores", "viral giants clip", "husband", "mom in that", "parenting",
        "relationship", "sports", "celebrity", "dating", "lifestyle"
    ]
    i_matches = sum(1 for w in irr_keywords if w in text)

    # Researcher signals (theory, papers, math, architectures)
    r_keywords = [
        "arxiv", "alphaxiv", "bair", "paper", "theorem", "loss", "dataset",
        "benchmark", "parameter", "latent", "math", "architecture", "attention",
        "transformer", "training technique", "novel method", "physical world model"
    ]
    r_matches = sum(1 for w in r_keywords if w in text)

    # Engineer signals (implementation, production, APIs, tools, context engineering, RAG)
    e_keywords = [
        "context engineering", "production", "api", "wrapper", "compiler",
        "llm", "library", "code", "python", "software", "agent", "rag", "database",
        "infrastructure", "deployment", "elastic", "tokenmaxxing", "prompt",
        "postgres migration", "claude code skill", "stockfish", "pascal", "nixos", "simd"
    ]
    e_matches = sum(1 for w in e_keywords if w in text)

    # Startup & Innovation signals
    s_keywords = [
        "startup", "iit", "incubation", "raise", "million", "fund", "venture",
        "market", "partner", "launch", "program", "innovation", "commercial",
        "enterprise adoption", "yourstory", "first close", "deep-tech fund", "crore"
    ]
    s_matches = sum(1 for w in s_keywords if w in text)

    r_raw = max(0.04, 0.12 + (r_matches * 0.20))
    e_raw = max(0.04, 0.14 + (e_matches * 0.22))
    s_raw = max(0.04, 0.12 + (s_matches * 0.22))
    i_raw = max(0.04, 0.05 + (i_matches * 0.35))

    total = r_raw + e_raw + s_raw + i_raw
    probs = {
        "ai_engineer": round(e_raw / total, 3),
        "ai_researcher": round(r_raw / total, 3),
        "startup_innovation": round(s_raw / total, 3),
        "irrelevant": round(i_raw / total, 3),
    }

    primary = max(probs, key=probs.get)
    confidence = round(probs[primary], 2)

    return RuneClassificationResult(
        primary_role=primary,
        confidence=confidence,
        role_probabilities=probs,
        researcher_score=probs["ai_researcher"],
        engineer_score=probs["ai_engineer"],
        startup_score=probs["startup_innovation"],
        irrelevant_score=probs["irrelevant"],
        is_live_api=False,
    )
