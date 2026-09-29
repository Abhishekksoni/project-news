"""Shared taxonomy, detailed role prompts, criteria, and label definitions for 3-role decision classification."""

from typing import Dict, List

ROLES: List[str] = ["ai_researcher", "ai_engineer", "startup_innovations", "noise"]

LABEL2ID: Dict[str, int] = {
    "ai_researcher": 0,
    "ai_engineer": 1,
    "startup_innovations": 2,
    "noise": 3,
}

ID2LABEL: Dict[int, str] = {
    0: "ai_researcher",
    1: "ai_engineer",
    2: "startup_innovations",
    3: "noise",
}

ROLE_DISPLAY_NAMES: Dict[str, str] = {
    "ai_researcher": "🔬 AI_ML Researcher",
    "ai_engineer": "🧑‍💻 Software / AI Engineer",
    "startup_innovations": "🚀 Innovation and Startups",
    "noise": "🗑️ Noise / Off-Topic",
}

# Dedicated prompt criteria for each role to guide Jev AI decision scoring
ROLE_CRITERIA: Dict[str, str] = {
    "ai_researcher": (
        "Focuses on scientific AI/ML research, machine learning theory, novel neural network architectures, "
        "mathematical loss formulations, training dynamics, scaling laws, empirical benchmark evaluations, "
        "reinforcement learning theory, mechanistic interpretability, and academic preprints (e.g., arXiv, AlphaXiv, NeurIPS, ICML)."
    ),
    "ai_engineer": (
        "Focuses on practical software engineering and AI implementation, developer tooling, open-source code repositories, "
        "Python packages, APIs, SDKs, LLM application frameworks (e.g., LangChain, LlamaIndex), agent orchestration, "
        "inference acceleration & runtimes (e.g., vLLM, llama.cpp, Ollama, TensorRT), quantization, Docker/Kubernetes deployment, "
        "and production software architecture."
    ),
    "startup_innovations": (
        "Focuses on technology startups, venture capital funding rounds (Seed, Series A-D, IPOs), commercial AI product launches, "
        "founder stories, entrepreneurship, mergers & acquisitions, enterprise partnerships, business model innovations, "
        "executive leadership moves, and commercial tech industry market trends."
    ),
    "noise": (
        "The news item does not provide meaningful or direct value to any of the "
        "three target audiences: AI/ML researchers, AI/software engineers, or "
        "startup/founder/innovation audiences.\n\n"
        "Examples include:\n"
        "- General technology news with no meaningful AI/ML, engineering, or startup relevance\n"
        "- Consumer product announcements with no relevant technical or business insight\n"
        "- Celebrity/general entertainment news\n"
        "- Sports news\n"
        "- Generic political/social news unrelated to the target audiences\n"
        "- Repetitive or extremely low-information content\n"
        "- News where the AI/startup/engineering connection is merely incidental"
    ),
}

# NLI Entailment Hypotheses for Jev Cross-Encoder evaluation
ROLE_HYPOTHESES: Dict[str, str] = {
    "ai_researcher": (
        "This article is primarily targeted at AI and Machine Learning researchers, exploring academic research papers, "
        "deep learning theory, mathematical algorithms, novel neural architectures, training loss functions, or benchmark experiments."
    ),
    "ai_engineer": (
        "This article is primarily targeted at software and AI engineers, discussing practical code implementations, "
        "developer tooling, SDKs, APIs, open-source repositories, inference engines, model deployment, or software architecture."
    ),
    "startup_innovations": (
        "This article is primarily targeted at startup founders, tech entrepreneurs, and investors, discussing venture capital funding, "
        "commercial product launches, startup growth, acquisitions, business innovation, or tech industry market developments."
    ),
    "noise": (
        "This article is irrelevant, noise, or off-topic, offering no meaningful value to AI researchers, software engineers, or startup founders."
    ),
}

# Prompt guidelines for LLM / Jev System-1 prompt construction
ROLE_SYSTEM_PROMPT = """You are an expert AI decision classifier for a technical news intelligence platform.
Evaluate the article based on its Title, Content Snippet, and Source, and classify it into exactly one of four roles:

1. AI_ML RESEARCHER (ai_researcher):
   - Target Audience: Research scientists, ML theorists, academic researchers, PhDs.
   - Core Signals: Novel machine learning research, preprints, math/algorithms, training curves, transformer theory, benchmark leaderboards, academic papers.

2. SOFTWARE / AI ENGINEER (ai_engineer):
   - Target Audience: Software engineers, AI application builders, MLOps engineers, backend developers.
   - Core Signals: Practical code implementation, GitHub repositories, Python packages, SDKs, APIs, developer tools, LLM frameworks, inference engines (vLLM, Ollama, llama.cpp), model serving, deployment.

3. INNOVATION AND STARTUPS (startup_innovations):
   - Target Audience: Founders, startup teams, venture capitalists, product leaders, tech innovators.
   - Core Signals: Venture capital funding, seed/Series rounds, commercial product releases, startup stories, acquisitions, company valuations, tech business models, market expansion.

4. NOISE / OFF-TOPIC (noise):
   - Target Audience: None / Irrelevant.
   - Core Signals: General consumer gadgets, gossip, celebrity/sports news, non-technical commentary, spam, or news with zero actionable signal for AI researchers, engineers, or founders.

Select the single winning role that derives the most direct actionable value from this news, and output calibrated probability scores across all 4 roles.
"""
