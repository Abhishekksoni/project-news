import Database from "better-sqlite3";
import path from "path";
import fs from "fs";

export interface NewsItemRecord {
  id: string;
  title: string;
  url: string;
  source: string;
  source_type: string;
  published_at: string | null;
  author: string | null;
  description: string | null;
  category: string | null;
  image_url: string | null;
  is_duplicate: number;
  duplicate_of: string | null;
  primary_role: string | null;
  confidence: number;
  researcher_score: number;
  engineer_score: number;
  startup_score: number;
  noise_score: number;
  irrelevant_score?: number;
  collected_at: string;
}

export interface StatsRecord {
  total: number;
  unique: number;
  duplicates: number;
  roles: {
    ai_researcher: number;
    ai_engineer: number;
    startup_innovations: number;
    noise: number;
  };
  sources: Array<{ source: string; count: number }>;
  avg_confidence: number;
}

let dbInstance: Database.Database | null = null;

export function getDb(): Database.Database | null {
  if (dbInstance) return dbInstance;

  const possiblePaths = [
    path.resolve(process.cwd(), "../news.db"),
    path.resolve(process.cwd(), "news.db"),
    path.resolve(__dirname, "../../../news.db"),
  ];

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      try {
        dbInstance = new Database(p, { readonly: true });
        return dbInstance;
      } catch (err) {
        console.error(`[DB Error connecting to ${p}]:`, err);
      }
    }
  }

  return null;
}
