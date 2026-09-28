"""Test script for OpenJev (AlexWortega/openjev) classification across 3 target roles."""

import json
from classification.jev_client import (
    OPENJEV_MODEL,
    classify_with_jev,
)


def test_jev_on_sample_news():
    # 3 distinct test samples
    samples = [
        {
            "title": "Scaling Law for Latent Reasoning in Large Multimodal Models",
            "description": "We establish mathematical bounds and compute loss curves for multimodal chain-of-thought token generation.",
            "source": "AlphaXiv / arXiv Research",
        },
        {
            "title": "vLLM 0.6.0: PagedAttention Engine with Distributed CUDA Kernels and Fast Python Bindings",
            "description": "New release features memory-efficient KV cache paging, OpenAI-compatible HTTP API server, and dockerized deployment.",
            "source": "GitHub Trending / Engineering",
        },
        {
            "title": "The 10 Best Ergonomic Standing Desks and Espresso Machines for Your Home Office (2026)",
            "description": "Our editors tested over 25 adjustable wooden desks and coffee grinders to find the best daily comfort gear.",
            "source": "Lifestyle & Consumer Review",
        },
    ]

    print("=" * 80)
    print(f" OPENJEV ({OPENJEV_MODEL}) - 3-ROLE CLASSIFICATION TEST")
    print("=" * 80)

    for i, item in enumerate(samples, 1):
        title = item["title"]
        description = item["description"]
        source = item["source"]

        print(f"\n[{i}] ARTICLE: {title}")
        print(f"    Source: {source}")
        print(f"    Snippet: {description[:110]}...")

        # Run Classification
        result = classify_with_jev(title, description, source)

        print("\n    🎯 OPENJEV 3-ROLE DECISION:")
        print(f"       Primary Role:        👉 {result.primary_role.upper()} (Confidence: {result.confidence * 100:.1f}%)")
        print("       Role Probabilities: ", json.dumps(result.role_probabilities))
        print("       Scores Breakdown:")
        print(f"         1. 🔬 AI Researcher:            {result.researcher_score * 100:.1f}%")
        print(f"         2. 🧑‍💻 AI & Software Engineer:   {result.engineer_score * 100:.1f}%")
        print(f"         3. 🗑️ Noise / Irrelevant:       {result.noise_score * 100:.1f}%")
        print("-" * 80)


if __name__ == "__main__":
    test_jev_on_sample_news()
