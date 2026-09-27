"""Dedicated test script for testing the Rune 26B-A4B decision model."""

import json
from classification.rune_client import classify_with_rune, build_rune_request


def test_rune():
    test_articles = [
        {
            "title": "From tokenmaxxing to context engineering: Why enterprise AI needs better context, not bigger prompts",
            "description": "Drawing on Elastic's experience helping enterprises build AI for production, Head of Field Engineering Ravindra Ramnani explains why context engineering is emerging as the next critical discipline for enterprise AI.",
            "source": "YourStory",
        },
        {
            "title": "InternW0: A Foundational Physical World Model for Efficient Real-World Interactions",
            "description": "InternW0 combines long-horizon video prediction with fast continuous robot control in an asynchronous physical world model.",
            "source": "AlphaXiv",
        },
        {
            "title": "Chevron ENGINE and IIT Madras launch Energy Technology Incubation program",
            "description": "Chevron ENGINE and IIT Madras launch Energy Technology Incubation program to support energy innovation and startup incubation.",
            "source": "India Education Diary",
        },
    ]

    print("=" * 80)
    print(" RUNE 26B-A4B (SUROGATE) - 3-ROLE DECISION TEST")
    print("=" * 80)

    for i, item in enumerate(test_articles, 1):
        title = item["title"]
        desc = item["description"]
        source = item["source"]

        print(f"\n[{i}] ARTICLE: {title}")
        print(f"    Source: {source}")
        print(f"    Snippet: {desc[:110]}...")

        # 1. Payload structure
        payload = build_rune_request(title, desc, source)
        print("\n    📝 Candidate Role Targets Evaluated:")
        for idx, lbl in enumerate(payload["parameters"]["candidate_labels"], 1):
            print(f"       {idx}. {lbl[:60]}...")

        # 2. Run Classification
        result = classify_with_rune(title, desc, source)

        print("\n    🎯 RUNE 26B DECISION & SCORES:")
        print(f"       Mode: {'🟢 Live API' if result.is_live_api else '🟡 Test Mode'}")
        print(f"       Primary Role:        👉 {result.primary_role.upper()} (Confidence: {result.confidence * 100:.1f}%)")
        print("       Role Probabilities: ", json.dumps(result.role_probabilities))
        print("       Individual Scores (0.0 - 1.0):")
        print(f"         1. 🧑‍💻 AI Engineer / Developer:  {result.engineer_score * 100:.1f}%")
        print(f"         2. 🔬 AI / ML Researcher:       {result.researcher_score * 100:.1f}%")
        print(f"         3. 🚀 Startup & Innovation:     {result.startup_score * 100:.1f}%")
        print("-" * 80)


if __name__ == "__main__":
    test_rune()
