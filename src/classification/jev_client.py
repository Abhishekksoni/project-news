"""TypeSafe AI Jev System One (https://console.typesafe.ai) client for 3-role decision classification.

Direct API client for TypeSafe AI System One decision engine (POST https://api.typesafe.ai/v1/systemone).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, Field

from classification.taxonomy import (
    ROLE_CRITERIA,
    ROLE_DISPLAY_NAMES,
    ROLES,
)

load_dotenv()

DEFAULT_TYPESAFE_BASE_URL = "https://api.typesafe.ai"
DEFAULT_JEV_MODEL = "jev-latest"
JEV_MODEL = DEFAULT_JEV_MODEL


class JevClassificationResult(BaseModel):
    """Structured decision output from TypeSafe AI Jev across 4 audience roles."""

    primary_role: str = Field(
        description="The winning role: ai_researcher, ai_engineer, startup_innovations, or noise"
    )
    confidence: float = Field(
        description="Confidence score for the primary choice (0.0 - 1.0)"
    )
    role_probabilities: Dict[str, float] = Field(
        description="Probability distribution across the 4 roles",
    )
    researcher_score: float = Field(
        description="Probability score for AI_ML Researcher",
    )
    engineer_score: float = Field(
        description="Probability score for Software / AI Engineer",
    )
    startup_score: float = Field(
        description="Probability score for Innovation and Startups",
    )
    noise_score: float = Field(
        default=0.0,
        description="Probability score for Noise / Off-Topic news",
    )
    model: str = Field(
        default=DEFAULT_JEV_MODEL,
        description="Model identifier used for classification",
    )
    raw_response: Optional[Dict[str, Any]] = None


def classify_with_jev(
    title: str,
    description: str,
    source: str,
    api_key: str | None = None,
    timeout: float = 30.0,
) -> JevClassificationResult:
    """Classify a news item into one of 4 roles using TypeSafe AI Jev (console.typesafe.ai)."""
    token = (
        api_key
        or os.getenv("TYPESAFE_API_KEY")
        or os.getenv("JEV_API_KEY")
    )
    if not token or not token.strip():
        raise ValueError(
            "Missing TypeSafe API Key. Please set TYPESAFE_API_KEY or JEV_API_KEY in your .env file."
        )

    base_url = os.getenv("TYPESAFE_BASE_URL", DEFAULT_TYPESAFE_BASE_URL).rstrip("/")
    endpoint = f"{base_url}/v1/systemone"
    model = os.getenv("TYPESAFE_MODEL", os.getenv("JEV_MODEL", DEFAULT_JEV_MODEL))

    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    desc_clean = description.strip()
    if len(desc_clean) > 350:
        desc_clean = desc_clean[:350].rsplit(" ", 1)[0] + "..."

    state_context = (
        f"Title: {title.strip()}\n"
        f"Source: {source.strip()}\n"
        f"Description / Content: {desc_clean}"
    )

    payload = {
        "model": model,
        "state": state_context,
        "questions": {
            "role": {
                "type": "choice",
                "instructions": (
                    "Evaluate this news item and determine which audience role derives the most direct value from it, or if it is noise/off-topic."
                ),
                "criteria": {
                    "ai_researcher": ROLE_CRITERIA["ai_researcher"],
                    "ai_engineer": ROLE_CRITERIA["ai_engineer"],
                    "startup_innovations": ROLE_CRITERIA["startup_innovations"],
                    "noise": ROLE_CRITERIA["noise"],
                },
            }
        },
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            raise RuntimeError(
                f"TypeSafe Jev API request failed [Status {response.status_code}]: {response.text}"
            )
        data = response.json()

    answers = data.get("answers", {})
    role_answer = answers.get("role", {}) or data.get("role", {})

    if not role_answer:
        raise ValueError(f"TypeSafe Jev API returned empty question answers: {data}")

    # Extract probabilities
    raw_probs = role_answer.get("probabilities", {})
    if not isinstance(raw_probs, dict) or not raw_probs:
        # If choice is returned with confidence
        if "choice" in role_answer:
            chosen = role_answer["choice"]
            conf = float(role_answer.get("confidence", 1.0))
            raw_probs = {r: (conf if r == chosen else 0.0) for r in ROLES}
        else:
            raise ValueError(f"TypeSafe Jev API response missing role probabilities: {role_answer}")

    role_probs: Dict[str, float] = {}
    for r in ROLES:
        if r in raw_probs:
            role_probs[r] = round(float(raw_probs[r]), 4)

    if not role_probs:
        raise ValueError(f"No valid role probabilities in TypeSafe Jev response: {role_answer}")

    chosen_role = role_answer.get("choice")
    if chosen_role and chosen_role in role_probs:
        primary_role = chosen_role
    else:
        primary_role = max(role_probs, key=role_probs.get)

    confidence = float(role_answer.get("confidence", role_probs.get(primary_role, 0.0)))

    return JevClassificationResult(
        primary_role=primary_role,
        confidence=confidence,
        role_probabilities=role_probs,
        researcher_score=role_probs.get("ai_researcher", 0.0),
        engineer_score=role_probs.get("ai_engineer", 0.0),
        startup_score=role_probs.get("startup_innovations", 0.0),
        noise_score=role_probs.get("noise", 0.0),
        model=model,
        raw_response=data,
    )
