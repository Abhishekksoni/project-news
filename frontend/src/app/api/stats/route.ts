import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { supabase } from "@/lib/supabase";

export async function GET() {
  if (supabase) {
    try {
      const { count: total } = await supabase.from("news_items").select("*", { count: "exact", head: true });
      const { count: duplicates } = await supabase.from("news_items").select("*", { count: "exact", head: true }).eq("is_duplicate", true);
      
      const { data: rows } = await supabase.from("news_items").select("primary_role, source, confidence");
      if (rows) {
        const rolesMap = {
          ai_researcher: 0,
          ai_engineer: 0,
          startup_innovations: 0,
          noise: 0,
        };
        const sourceCountMap: Record<string, number> = {};
        let confSum = 0;
        let confCount = 0;

        for (const r of rows) {
          if (r.primary_role && r.primary_role in rolesMap) {
            rolesMap[r.primary_role as keyof typeof rolesMap]++;
          }
          if (r.source) {
            sourceCountMap[r.source] = (sourceCountMap[r.source] || 0) + 1;
          }
          if (r.confidence && r.confidence > 0) {
            confSum += r.confidence;
            confCount++;
          }
        }

        const sources = Object.entries(sourceCountMap)
          .map(([source, count]) => ({ source, count }))
          .sort((a, b) => b.count - a.count);

        const totalNum = total || rows.length;
        const dupNum = duplicates || 0;

        return NextResponse.json({
          total: totalNum,
          unique: totalNum - dupNum,
          duplicates: dupNum,
          roles: rolesMap,
          sources,
          avg_confidence: confCount > 0 ? Math.round((confSum / confCount) * 100) / 100 : 0.85,
        });
      }
    } catch (sbError) {
      console.warn("Supabase stats error, falling back to local DB:", sbError);
    }
  }

  const db = getDb();
  if (!db) {
    return NextResponse.json({
      total: 0,
      unique: 0,
      duplicates: 0,
      roles: { ai_researcher: 0, ai_engineer: 0, startup_innovations: 0, noise: 0 },
      sources: [],
      avg_confidence: 0,
    });
  }

  try {
    const totalRow = db.prepare("SELECT count(*) as count FROM news_items").get() as { count: number };
    const dupRow = db.prepare("SELECT count(*) as count FROM news_items WHERE is_duplicate = 1").get() as { count: number };
    const avgConfRow = db.prepare("SELECT AVG(confidence) as avg_conf FROM news_items WHERE confidence > 0").get() as { avg_conf: number };

    const roleRows = db.prepare(`
      SELECT primary_role, count(*) as count 
      FROM news_items 
      GROUP BY primary_role
    `).all() as Array<{ primary_role: string | null; count: number }>;

    const sourceRows = db.prepare(`
      SELECT source, count(*) as count 
      FROM news_items 
      GROUP BY source 
      ORDER BY count DESC
    `).all() as Array<{ source: string; count: number }>;

    const rolesMap = {
      ai_researcher: 0,
      ai_engineer: 0,
      startup_innovations: 0,
      noise: 0,
    };

    for (const r of roleRows) {
      if (r.primary_role && r.primary_role in rolesMap) {
        rolesMap[r.primary_role as keyof typeof rolesMap] = r.count;
      }
    }

    return NextResponse.json({
      total: totalRow?.count || 0,
      unique: (totalRow?.count || 0) - (dupRow?.count || 0),
      duplicates: dupRow?.count || 0,
      roles: rolesMap,
      sources: sourceRows,
      avg_confidence: Math.round((avgConfRow?.avg_conf || 0) * 100) / 100,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Database error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
