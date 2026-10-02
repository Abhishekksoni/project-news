import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// Read API keys from root .env if not present in process.env
function getApiKey(): string | null {
  if (process.env.TYPESAFE_API_KEY) return process.env.TYPESAFE_API_KEY;
  if (process.env.JEV_API_KEY) return process.env.JEV_API_KEY;

  try {
    const rootEnvPath = path.resolve(process.cwd(), "../.env");
    if (fs.existsSync(rootEnvPath)) {
      const content = fs.readFileSync(rootEnvPath, "utf-8");
      const match = content.match(/(?:TYPESAFE_API_KEY|JEV_API_KEY)=([^\r\n]+)/);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
  } catch {
    // Ignore error
  }
  return null;
}

const ROLE_CRITERIA = {
  ai_researcher:
    "Novel AI/ML theoretical advances, mathematical formulations, foundational model architectures, novel training algorithms, pre-training techniques, loss functions, benchmark evaluations, empirical scaling laws, and arXiv/alphaXiv academic papers.",
  ai_engineer:
    "Applied software engineering with AI, open-source repositories, developer tooling, SDKs, APIs, model inference optimization, quantization, fine-tuning scripts, vLLM/Ollama deployments, local LLM tooling, Hugging Face models/pipelines, agent frameworks, MCP servers, and infrastructure.",
  startup_innovations:
    "New AI startups, product launches, venture capital funding rounds, commercial consumer/enterprise AI apps, market disruptions, acquisitions, business partnerships, executive shifts, and new proprietary commercial models.",
  noise:
    "Unrelated tech news, general politics, generic non-AI software updates, gadget reviews, standard crypto/blockchain market chatter, routine corporate PR without technical or commercial AI substance, and off-topic posts.",
};

export async function POST(req: NextRequest) {
  try {
    const { title, description, source } = await req.json();

    if (!title) {
      return NextResponse.json({ error: "Title is required" }, { status: 400 });
    }

    const apiKey = getApiKey();
    if (!apiKey) {
      return NextResponse.json(
        { error: "Missing TYPESAFE_API_KEY in environment" },
        { status: 400 }
      );
    }

    // Apply 350-character limit
    let descClean = (description || "").trim();
    if (descClean.length > 350) {
      const idx = descClean.slice(0, 350).lastIndexOf(" ");
      descClean = (idx > 0 ? descClean.slice(0, idx) : descClean.slice(0, 350)) + "...";
    }

    const stateContext = `Title: ${title.trim()}\nSource: ${(source || "Custom Input").trim()}\nDescription / Content: ${descClean}`;

    const payload = {
      model: "jev-latest",
      state: stateContext,
      questions: {
        role: {
          type: "choice",
          instructions:
            "Evaluate this news item and determine which audience role derives the most direct value from it, or if it is noise/off-topic.",
          criteria: ROLE_CRITERIA,
        },
      },
    };

    const response = await fetch("https://api.typesafe.ai/v1/systemone", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errText = await response.text();
      return NextResponse.json(
        { error: `TypeSafe Jev API returned ${response.status}: ${errText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    const roleAnswer = data.answers?.role || data.role;

    if (!roleAnswer) {
      return NextResponse.json({ error: "Empty answer from Jev API", raw: data }, { status: 500 });
    }

    const probabilities = roleAnswer.probabilities || {};
    const chosenRole = roleAnswer.choice || Object.keys(probabilities)[0] || "ai_engineer";
    const confidence = roleAnswer.confidence || probabilities[chosenRole] || 1.0;

    return NextResponse.json({
      primary_role: chosenRole,
      confidence: Math.round(confidence * 100) / 100,
      probabilities: {
        ai_researcher: Math.round((probabilities.ai_researcher || 0) * 100) / 100,
        ai_engineer: Math.round((probabilities.ai_engineer || 0) * 100) / 100,
        startup_innovations: Math.round((probabilities.startup_innovations || 0) * 100) / 100,
        noise: Math.round((probabilities.noise || 0) * 100) / 100,
      },
      processed_description: descClean,
      raw: data,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Classification failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
