"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Sparkles,
  AlertCircle,
  FileQuestion,
  Search,
  ArrowUp,
} from "lucide-react";
import { Header } from "@/components/Header";
import { OrbitaHero } from "@/components/OrbitaHero";
import { RoleFilters } from "@/components/RoleFilters";
import { TelemetryBar } from "@/components/TelemetryBar";
import { MasonryFeed } from "@/components/MasonryFeed";
import { InspectorModal } from "@/components/InspectorModal";
import { BookmarksDrawer } from "@/components/BookmarksDrawer";
import { NewsItemRecord, StatsRecord } from "@/lib/db";
import { soundFX } from "@/lib/sounds";

export default function Home() {
  const [items, setItems] = useState<NewsItemRecord[]>([]);
  const [stats, setStats] = useState<StatsRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & State
  const [activeRole, setActiveRole] = useState<string>("all");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [hideDuplicates, setHideDuplicates] = useState<boolean>(true);
  const [activeSort, setActiveSort] = useState<string>("newest");
  const PAGE_SIZE = 24;
  const [totalCount, setTotalCount] = useState<number>(0);

  // Sentinel ref for infinite scroll
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // UI Modals & Effects
  const [scanlinesEnabled, setScanlinesEnabled] = useState<boolean>(false);
  const [inspectorItem, setInspectorItem] = useState<NewsItemRecord | null>(null);
  const [isBookmarksOpen, setIsBookmarksOpen] = useState<boolean>(false);
  const [showScrollTop, setShowScrollTop] = useState<boolean>(false);

  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Load Theme from LocalStorage
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("project_news_theme") as "dark" | "light" | null;
      if (savedTheme === "light" || savedTheme === "dark") {
        setTheme(savedTheme);
        document.documentElement.classList.remove("light", "dark");
        document.documentElement.classList.add(savedTheme);
      } else {
        document.documentElement.classList.add("dark");
      }
    } catch { }
  }, []);

  // Window scroll listener for "Back to Top" button
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 350) {
        setShowScrollTop(true);
      } else {
        setShowScrollTop(false);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleScrollToTop = () => {
    soundFX.playBlip(900);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleToggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    try {
      localStorage.setItem("project_news_theme", nextTheme);
      document.documentElement.classList.remove("light", "dark");
      document.documentElement.classList.add(nextTheme);
    } catch { }
  };

  // Fetch Stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch { }
  }, []);

  // Fetch initial batch of news items whenever filters change
  const fetchInitialNews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        role: activeRole,
        source: selectedSource,
        q: searchQuery,
        hide_duplicates: hideDuplicates ? "true" : "false",
        sort: activeSort,
        limit: PAGE_SIZE.toString(),
        offset: "0",
      });

      const res = await fetch(`/api/news?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`HTTP Error ${res.status}`);
      }
      const data = await res.json();
      const initialItems: NewsItemRecord[] = data.items || [];
      const total = data.total || 0;

      setItems(initialItems);
      setTotalCount(total);
      setHasMore(initialItems.length < total && initialItems.length > 0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load telemetry feed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [activeRole, selectedSource, searchQuery, hideDuplicates, activeSort]);

  // Load next batch on scroll
  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return;
    setLoadingMore(true);

    try {
      const currentOffset = items.length;
      const params = new URLSearchParams({
        role: activeRole,
        source: selectedSource,
        q: searchQuery,
        hide_duplicates: hideDuplicates ? "true" : "false",
        sort: activeSort,
        limit: PAGE_SIZE.toString(),
        offset: currentOffset.toString(),
      });

      const res = await fetch(`/api/news?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`HTTP Error ${res.status}`);
      }
      const data = await res.json();
      const newItems: NewsItemRecord[] = data.items || [];
      const total = data.total || totalCount;

      setItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        const uniqueIncoming = newItems.filter((i) => !existingIds.has(i.id));
        const combined = [...prev, ...uniqueIncoming];
        setHasMore(combined.length < total && newItems.length > 0);
        return combined;
      });
      setTotalCount(total);
    } catch {
      // Retry on next scroll
    } finally {
      setLoadingMore(false);
    }
  }, [loading, loadingMore, hasMore, items.length, totalCount, activeRole, selectedSource, searchQuery, hideDuplicates, activeSort]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchInitialNews();
  }, [fetchInitialNews]);

  // IntersectionObserver Sentinel for Infinite Scrolling
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading && !loadingMore) {
          loadMore();
        }
      },
      { rootMargin: "600px 0px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore, hasMore, loading, loadingMore]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="min-h-screen orbita-grid-bg relative text-slate-100 flex flex-col selection:bg-[#e27d42]/40 selection:text-white">
      {/* CRT Scanline Overlay if toggled */}
      {scanlinesEnabled && <div className="scanlines fixed inset-0 z-50 pointer-events-none" />}

      {/* Header with Expandable Search */}
      <Header
        theme={theme}
        onToggleTheme={handleToggleTheme}
        scanlinesEnabled={scanlinesEnabled}
        setScanlinesEnabled={setScanlinesEnabled}
        onOpenBookmarks={() => setIsBookmarksOpen(true)}
        searchQuery={searchQuery}
        onSearchChange={(q) => setSearchQuery(q)}
      />

      {/* Hero 50vh Image Banner with Quote */}
      <OrbitaHero />

      {/* Main Signal Feed Container */}
      <main className="max-w-[1600px] w-full mx-auto px-3 sm:px-6 lg:px-12 py-6 sm:py-8 space-y-6 sm:space-y-8 flex-1">
        {/* Role Filters (4 Audience Roles + All Signals) */}
        <div className="space-y-3">
          <RoleFilters
            activeRole={activeRole}
            onSelectRole={(role) => setActiveRole(role)}
            counts={stats?.roles}
            totalCount={stats?.total || totalCount}
          />
        </div>

        {/* Telemetry Statistics & Source Nodes Bar */}
        <TelemetryBar
          stats={stats}
          selectedSource={selectedSource}
          onSelectSource={(src) => setSelectedSource(src)}
          activeSort={activeSort}
          onSelectSort={(sort) => {
            soundFX.playBlip(750);
            setActiveSort(sort);
          }}
        />

        {/* Loading State for initial fetch */}
        {loading && (
          <div className="py-24 flex flex-col items-center justify-center space-y-4">
            <div className="relative flex items-center justify-center">
              <div className="w-12 h-12 rounded-full border-2 border-[#e27d42]/30 border-t-[#e27d42] animate-spin" />
              <Sparkles className="w-5 h-5 text-[#e27d42] absolute animate-pulse" />
            </div>
            <div className="font-mono text-xs text-[#e27d42] tracking-widest uppercase">
              SCANNING ORBITAL TELEMETRY...
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="p-8 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 font-mono text-xs flex flex-col items-center justify-center text-center space-y-3">
            <AlertCircle className="w-8 h-8 text-red-400" />
            <div>{error}</div>
            <button
              onClick={() => fetchInitialNews()}
              className="px-5 py-2 rounded-xl bg-red-900/60 hover:bg-red-800 text-white font-bold border border-red-500/50 transition-all cursor-pointer"
            >
              RETRY CONNECTION
            </button>
          </div>
        )}

        {/* Pinterest Masonry Signal Cards Feed */}
        {!loading && !error && items.length > 0 && (
          <MasonryFeed
            items={items}
            onInspect={(selected) => setInspectorItem(selected)}
          />
        )}

        {/* Empty State */}
        {!loading && !error && items.length === 0 && (
          <div className="py-24 flex flex-col items-center justify-center text-center space-y-3 bg-[#0c0609]/80 rounded-2xl border border-white/10 p-10">
            <FileQuestion className="w-12 h-12 text-gray-600" />
            <div className="font-['Rajdhani',sans-serif] text-base font-bold text-gray-300 uppercase tracking-wider">
              NO ORBITAL SIGNALS DETECTED
            </div>
            <p className="text-xs text-gray-500 max-w-sm font-sans">
              No intelligence items matched your current filter criteria. Reset filters to stream all available signals.
            </p>
            <button
              onClick={() => {
                setActiveRole("all");
                setSelectedSource("all");
                setSearchQuery("");
                setHideDuplicates(false);
              }}
              className="px-5 py-2.5 rounded-xl bg-[#e27d42]/20 hover:bg-[#e27d42]/30 text-[#f59e0b] border border-[#e27d42]/50 font-mono text-xs font-bold transition-all cursor-pointer"
            >
              RESET ALL STREAM FILTERS
            </button>
          </div>
        )}

        {/* Infinite Scroll Stream Sentinel & Bottom Loader */}
        {!loading && !error && items.length > 0 && (
          <div className="pt-4 pb-12 flex flex-col items-center justify-center space-y-3 font-mono text-xs text-stone-500 dark:text-gray-400">
            {/* Sentinel for IntersectionObserver */}
            <div ref={sentinelRef} className="h-4 w-full" />

            {loadingMore && (
              <div className="flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-stone-100 dark:bg-white/5 border border-stone-300 dark:border-white/10 shadow-sm animate-pulse">
                <div className="w-3.5 h-3.5 rounded-full border-2 border-[#e27d42]/30 border-t-[#e27d42] animate-spin" />
                <span className="text-[#e27d42] font-bold uppercase tracking-wider text-[11px]">
                  STREAMING NEXT ORBITAL BATCH...
                </span>
              </div>
            )}

            {!hasMore && items.length > 0 && (
              <div className="flex items-center gap-2 pt-4 text-[11px] uppercase tracking-widest text-stone-400 dark:text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full bg-[#e27d42]" />
                <span>END OF TELEMETRY STREAM • {totalCount} SIGNALS LOADED</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#e27d42]" />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-white/10 bg-[#050304] py-8 px-6 lg:px-12 mt-16 font-mono text-xs text-gray-500">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#e27d42] animate-pulse" />
            <span className="text-gray-300 font-bold">PROJECT NEWS</span>
            <span className="text-gray-600">•</span>
            <span>TYPESAFE JEV SYSTEM ONE</span>
          </div>
          <div className="text-gray-400">
            ENFORCING <span className="text-[#e27d42]">350-CHAR LIMIT</span> • <span className="text-emerald-400">LSH MINHASH DEDUPLICATED</span>
          </div>
        </div>
      </footer>

      {/* Tactical Inspector Modal */}
      <InspectorModal
        item={inspectorItem}
        onClose={() => setInspectorItem(null)}
      />

      {/* Mission Navigation & Role Switcher Drawer */}
      <BookmarksDrawer
        isOpen={isBookmarksOpen}
        onClose={() => setIsBookmarksOpen(false)}
        activeRole={activeRole}
        onSelectRole={(r) => {
          setActiveRole(r);
        }}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        scanlinesEnabled={scanlinesEnabled}
        setScanlinesEnabled={setScanlinesEnabled}
        stats={stats}
        totalCount={stats?.total || totalCount}
      />

      {/* Floating Back to Top Button */}
      {showScrollTop && (
        <button
          onClick={handleScrollToTop}
          title="Scroll back to top"
          className="fixed bottom-6 right-6 z-40 p-3 rounded-full dark:bg-[#0c070a]/90 bg-white/90 border dark:border-white/20 border-stone-300 dark:hover:border-[#e27d42] hover:border-[#e27d42] text-[#e27d42] shadow-2xl backdrop-blur-xl transition-all transform hover:scale-110 active:scale-95 cursor-pointer group animate-in fade-in duration-300 flex items-center justify-center"
        >
          <ArrowUp className="w-5 h-5 group-hover:-translate-y-0.5 transition-transform" />
        </button>
      )}
    </div>
  );
}
