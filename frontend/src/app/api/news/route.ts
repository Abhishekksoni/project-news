import { NextRequest, NextResponse } from "next/server";
import { getDb, NewsItemRecord } from "@/lib/db";
import { supabase } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const role = searchParams.get("role");
  const source = searchParams.get("source");
  const search = searchParams.get("q");
  const hideDuplicates = searchParams.get("hide_duplicates") === "true" || searchParams.get("hide_duplicates") === "1";
  const limit = Math.min(parseInt(searchParams.get("limit") || "100", 10), 500);
  const offset = parseInt(searchParams.get("offset") || "0", 10);
  const sort = searchParams.get("sort") || "newest"; // newest, confidence, researcher, engineer, startup

  // Try Supabase First (for Cloud Deployment)
  if (supabase) {
    try {
      let query = supabase.from("news_items").select("*", { count: "exact" });

      if (role && role !== "all") {
        query = query.eq("primary_role", role);
      } else {
        query = query.or("primary_role.neq.noise,primary_role.is.null");
      }

      if (source && source !== "all") {
        query = query.eq("source", source);
      } else {
        query = query.not("source", "in", '("Hugging Face Model Hub","GitHub Trending (Python & AI)")');
      }

      if (hideDuplicates) {
        query = query.or("is_duplicate.eq.false,is_duplicate.is.null");
      }

      if (search && search.trim()) {
        const term = search.trim();
        query = query.or(`title.ilike.%${term}%,description.ilike.%${term}%,author.ilike.%${term}%`);
      }

      if (sort === "confidence") {
        query = query.order("confidence", { ascending: false }).order("published_at", { ascending: false, nullsFirst: false });
      } else if (sort === "researcher") {
        query = query.order("researcher_score", { ascending: false }).order("published_at", { ascending: false, nullsFirst: false });
      } else if (sort === "engineer") {
        query = query.order("engineer_score", { ascending: false }).order("published_at", { ascending: false, nullsFirst: false });
      } else if (sort === "startup") {
        query = query.order("startup_score", { ascending: false }).order("published_at", { ascending: false, nullsFirst: false });
      } else if (sort === "noise") {
        query = query.order("noise_score", { ascending: false }).order("published_at", { ascending: false, nullsFirst: false });
      } else {
        query = query.order("published_at", { ascending: false, nullsFirst: false }).order("collected_at", { ascending: false });
      }

      query = query.range(offset, offset + limit - 1);

      const { data, count, error } = await query;
      if (!error && data) {
        return NextResponse.json({
          items: data as NewsItemRecord[],
          total: count || data.length,
          limit,
          offset,
        });
      }
    } catch (sbError) {
      console.warn("Supabase query error, falling back to local DB:", sbError);
    }
  }

  const db = getDb();
  if (!db) {
    return NextResponse.json(
      { error: "Database not found or unreachable.", items: [], total: 0 },
      { status: 200 }
    );
  }

  try {
    const conditions: string[] = [];
    const params: (string | number)[] = [];

    if (role && role !== "all") {
      conditions.push("primary_role = ?");
      params.push(role);
    } else {
      // In the general stream ("all"), exclude noise items
      conditions.push("(primary_role != 'noise' OR primary_role IS NULL)");
    }

    if (source && source !== "all") {
      conditions.push("source = ?");
      params.push(source);
    } else {
      // In the general stream ("all sources"), exclude standalone Hugging Face Model Hub & GitHub Repos
      // so they only appear in their dedicated separate section/source filters
      conditions.push("source NOT IN ('Hugging Face Model Hub', 'GitHub Trending (Python & AI)')");
    }

    if (hideDuplicates) {
      conditions.push("(is_duplicate = 0 OR is_duplicate IS NULL)");
    }

    if (search && search.trim()) {
      conditions.push("(title LIKE ? OR description LIKE ? OR author LIKE ?)");
      const term = `%${search.trim()}%`;
      params.push(term, term, term);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

    let orderBy = "COALESCE(published_at, collected_at) DESC, id DESC";
    if (sort === "newest" || !sort) {
      orderBy = "COALESCE(published_at, collected_at) DESC, id DESC";
    } else if (sort === "confidence") {
      orderBy = "confidence DESC, COALESCE(published_at, collected_at) DESC, id DESC";
    } else if (sort === "researcher") {
      orderBy = "researcher_score DESC, COALESCE(published_at, collected_at) DESC, id DESC";
    } else if (sort === "engineer") {
      orderBy = "engineer_score DESC, COALESCE(published_at, collected_at) DESC, id DESC";
    } else if (sort === "startup") {
      orderBy = "startup_score DESC, COALESCE(published_at, collected_at) DESC, id DESC";
    } else if (sort === "noise") {
      orderBy = "noise_score DESC, COALESCE(published_at, collected_at) DESC, id DESC";
    }

    const countQuery = `SELECT count(*) as count FROM news_items ${whereClause}`;
    const countRow = db.prepare(countQuery).get(...params) as { count: number };
    const totalCount = countRow?.count || 0;

    const dataQuery = `
      SELECT * FROM news_items
      ${whereClause}
      ORDER BY ${orderBy}
      LIMIT ? OFFSET ?
    `;

    const items = db.prepare(dataQuery).all(...params, limit, offset) as NewsItemRecord[];

    return NextResponse.json({
      items,
      total: totalCount,
      limit,
      offset,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown database error";
    return NextResponse.json({ error: message, items: [], total: 0 }, { status: 500 });
  }
}
