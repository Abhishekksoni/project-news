---
name: typesafe-ai
license: MIT
description: >
  Build AI-powered software with TypeSafe: small units of AI intelligence you
  can use like programming primitives. Its System One models, including Jev,
  turn natural language and application state into typed judgments and
  probabilities that code can combine. Use when a feature needs programmable
  common sense, when brainstorming what AI could make possible in an app, or
  when an LLM prompt-and-parse step could become a structured decision.
  Applications include routing, ranking, extraction, verification, and
  interactive experiences; these are starting points, not the limits.
  Read live docs and cookbooks to find useful patterns and discover new combinations.
---

# Build with TypeSafe

TypeSafe makes units of AI intelligence usable like programming primitives: small
judgments you can compose into larger capabilities. Its **System One models** return
fast, focused judgments that software can consume directly. **Jev** is TypeSafe's
flagship and first System One model. It understands natural language and returns
typed answers and probabilities rather than generating text or reasoning explanations.
Code owns the workflow; the model supplies programmable common sense where ordinary
code needs semantic understanding.

## Live Docs & References

- Documentation Index: https://docs.typesafe.ai/llms.txt
- HTTP API: https://docs.typesafe.ai/api.md
- Python SDK: https://docs.typesafe.ai/sdk/python.md
- Evaluation endpoint: `POST https://api.typesafe.ai/v1/systemone`
- Model: `jev-latest`
- Primitives: `choice`, `score`, `noul`
