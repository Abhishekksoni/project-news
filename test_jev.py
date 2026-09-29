"""Test script for Jev AI classification across 4 target roles including noise with dedicated prompts."""

import json
from pathlib import Path
import sys

src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from classification.jev_client import (
    JEV_MODEL,
    classify_with_jev,
)
from classification.taxonomy import ROLE_CRITERIA, ROLE_DISPLAY_NAMES


def test_jev_on_sample_news():
    # 4 distinct test samples representing each audience role + noise
    samples = [
        {
            "title": "Scaling Laws for Latent Reasoning in Large Multimodal Models",
            "description": "We establish mathematical bounds, transformer attention loss curves, and compute trade-offs for multimodal chain-of-thought token generation.",
            "source": "AlphaXiv / arXiv Research",
        },
        {
            "title": "vLLM 0.6.0: PagedAttention Engine with Distributed CUDA Kernels and Fast Python Bindings",
            "description": "New open-source release features memory-efficient KV cache paging, OpenAI-compatible HTTP server SDK, Dockerized deployment, and Triton kernels.",
            "source": "GitHub Trending / Engineering",
        },
        {
            "title": "Enterprise AI Startup Cohere Closes $500M Series D at $5B Valuation Led by Cisco and AMD",
            "description": "The enterprise foundation model startup backed by major tech giants plans to expand global go-to-market partnerships, corporate acquisitions, and revenue growth.",
            "source": "TechCrunch AI / Startups",
        },
        {
            "title": "Hollywood Star Debuts New Line of Glittery Phone Cases and Designer Sunglasses at Beach Party",
            "description": "Celebrities gather in Miami for the launch of a summer luxury accessory collection with cocktails, live DJ sets, and red carpet photo shoots.",
            "source": "Celebrity Daily News",
        },
    ]

    print("=" * 85)
    print(f" JEV AI ({JEV_MODEL}) - 4-ROLE DECISION CLASSIFICATION TEST (INCL. NOISE)")
    print("=" * 85)

    print("\n📋 ACTIVE ROLE PROMPT CRITERIA:")
    for role, criteria in ROLE_CRITERIA.items():
        print(f"  • {ROLE_DISPLAY_NAMES[role]}: {criteria[:100]}...")

    print("\n" + "-" * 85)

    for i, item in enumerate(samples, 1):
        title = item["title"]
        description = item["description"]
        source = item["source"]

        print(f"\n[{i}] ARTICLE: {title}")
        print(f"    Source:   {source}")
        print(f"    Snippet:  {description[:110]}...")

        # Run Classification
        result = classify_with_jev(title, description, source)

        print("\n    🎯 JEV AI DECISION:")
        print(f"       Primary Role:        👉 {ROLE_DISPLAY_NAMES.get(result.primary_role, result.primary_role)} (Conf: {result.confidence * 100:.1f}%)")
        print("       Role Probabilities: ", json.dumps(result.role_probabilities))
        print("       Scores Breakdown:")
        print(f"         1. 🔬 AI_ML Researcher:         {result.researcher_score * 100:.1f}%")
        print(f"         2. 🧑‍💻 Software / AI Engineer:  {result.engineer_score * 100:.1f}%")
        print(f"         3. 🚀 Innovation and Startups:  {result.startup_score * 100:.1f}%")
        print(f"         4. 🗑️ Noise / Off-Topic:        {result.noise_score * 100:.1f}%")
        print("-" * 85)


if __name__ == "__main__":
    test_jev_on_sample_news()
