"""Shared taxonomy and label definitions for Project News 3-role classification."""

from typing import Dict, List

ROLES: List[str] = ["ai_researcher", "ai_engineer", "noise"]

LABEL2ID: Dict[str, int] = {
    "ai_researcher": 0,
    "ai_engineer": 1,
    "noise": 2,
}

ID2LABEL: Dict[int, str] = {
    0: "ai_researcher",
    1: "ai_engineer",
    2: "noise",
}

ROLE_DISPLAY_NAMES: Dict[str, str] = {
    "ai_researcher": "🔬 AI & ML Research",
    "ai_engineer": "🧑‍💻 AI & Software Engineering",
    "noise": "🗑️ Noise / Irrelevant",
}

ROLE_CRITERIA: Dict[str, str] = {
    "ai_researcher": (
        "Novel Artificial Intelligence and Machine Learning research papers, deep learning theory, "
        "model architectures, mathematical algorithms, training loss formulations, benchmarks, and preprints."
    ),
    "ai_engineer": (
        "Practical AI engineering, software engineering, developer tooling, Python packages, "
        "APIs, SDKs, LLM frameworks, agent orchestration, inference kernels, deployment, and repositories."
    ),
    "noise": (
        "General non-technical news, sports, gaming, entertainment, lifestyle, non-technical business deals, "
        "unrelated physical retail products, clickbait, or irrelevant content."
    ),
}

ROLE_HYPOTHESES: Dict[str, str] = {
    "ai_researcher": "This text is primarily discussing novel machine learning research, mathematical algorithms, deep learning theory, training techniques, model architectures, or academic papers.",
    "ai_engineer": "This text is primarily discussing practical software engineering, developer tooling, Python packages, APIs, SDKs, runtime deployment, or code implementation.",
    "noise": "This text is primarily discussing non-technical topics, lifestyle, sports, entertainment, physical consumer products, or irrelevant noise.",
}
