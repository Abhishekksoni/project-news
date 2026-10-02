"use client";

import React from "react";
import {
  Activity,
  Layers,
  ShieldCheck,
  Zap,
  Filter,
  ArrowUpDown,
} from "lucide-react";
import { StatsRecord } from "@/lib/db";
import { trackEvent } from "@/app/providers";

interface TelemetryBarProps {
  stats: StatsRecord | null;
  selectedSource: string;
  onSelectSource: (source: string) => void;
  activeSort: string;
  onSelectSort: (sort: string) => void;
}

export const TelemetryBar: React.FC<TelemetryBarProps> = ({
  stats,
  selectedSource,
  onSelectSource,
  activeSort,
  onSelectSort,
}) => {
  const sources = stats?.sources || [];
  const total = stats?.total || 0;
  const unique = stats?.unique || 0;
  const duplicates = stats?.duplicates || 0;
  const avgConf = stats?.avg_confidence ? Math.round(stats.avg_confidence * 100) : 85;

  return (
    <div className="w-full dark:bg-[#0c0609]/90 bg-white/90 border dark:border-white/10 border-stone-200 rounded-2xl p-4 backdrop-blur-xl space-y-4 shadow-sm">
      {/* Top Telemetry Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
        <div className="flex items-center gap-3 p-3 rounded-xl dark:bg-black/40 bg-stone-50 border dark:border-white/5 border-stone-200">
          <Activity className="w-4 h-4 text-[#e27d42]" />
          <div>
            <div className="dark:text-gray-400 text-stone-500 text-[10px] uppercase">TOTAL SIGNALS</div>
            <div className="text-sm font-bold dark:text-white text-stone-900 tracking-wide">{total} INGESTED</div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-xl dark:bg-black/40 bg-stone-50 border dark:border-white/5 border-stone-200">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <div>
            <div className="dark:text-gray-400 text-stone-500 text-[10px] uppercase">LSH MINHASH DEDUP</div>
            <div className="text-sm font-bold dark:text-emerald-300 text-emerald-700 tracking-wide">{unique} ({duplicates} DUPES)</div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-xl dark:bg-black/40 bg-stone-50 border dark:border-white/5 border-stone-200">
          <Zap className="w-4 h-4 text-[#e27d42]" />
          <div>
            <div className="dark:text-gray-400 text-stone-500 text-[10px] uppercase">JEV CONFIDENCE</div>
            <div className="text-sm font-bold text-[#c25e24] dark:text-[#f59e0b] tracking-wide">{avgConf}% ACCURACY</div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-xl dark:bg-black/40 bg-stone-50 border dark:border-white/5 border-stone-200">
          <Layers className="w-4 h-4 text-cyan-500" />
          <div>
            <div className="dark:text-gray-400 text-stone-500 text-[10px] uppercase">ORBITAL STREAMS</div>
            <div className="text-sm font-bold dark:text-cyan-300 text-cyan-700 tracking-wide">{sources.length} SOURCES</div>
          </div>
        </div>
      </div>

      {/* Sources & Sort Side-by-Side Controls */}
      <div className="pt-3 border-t dark:border-white/5 border-stone-200">
        <div className="grid grid-cols-2 gap-2 sm:gap-3 w-full font-mono text-xs">
          {/* Sources Dropdown */}
          <div className="relative flex items-center w-full min-w-0">
            <div className="absolute left-2.5 sm:left-3 pointer-events-none text-[#e27d42] flex items-center gap-1 sm:gap-1.5">
              <Filter className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="hidden md:inline text-[10px] uppercase font-bold text-stone-500 dark:text-gray-400">
                SOURCE:
              </span>
            </div>
            <select
              value={selectedSource}
              onChange={(e) => {
                trackEvent("source_filter_changed", { source: e.target.value });
                onSelectSource(e.target.value);
              }}
              className="w-full dark:bg-black/60 bg-stone-100 border dark:border-white/15 border-stone-300 rounded-xl pl-7 sm:pl-8 md:pl-24 pr-6 sm:pr-8 py-2 sm:py-2.5 dark:text-gray-200 text-stone-800 text-[11px] sm:text-xs font-mono focus:outline-none focus:border-[#e27d42] hover:border-[#e27d42]/50 cursor-pointer truncate shadow-sm transition-all appearance-none"
            >
              <option value="all">ALL SOURCES ({total})</option>
              {sources.map((s) => (
                <option key={s.source} value={s.source}>
                  {s.source.replace(" (Python & AI)", "").replace(" (Medium)", "")} ({s.count})
                </option>
              ))}
            </select>
            <div className="absolute right-2 sm:right-3 pointer-events-none text-stone-400 dark:text-gray-500 text-[9px] sm:text-[10px]">
              ▼
            </div>
          </div>

          {/* Sort Dropdown */}
          <div className="relative flex items-center w-full min-w-0">
            <div className="absolute left-2.5 sm:left-3 pointer-events-none text-[#e27d42] flex items-center gap-1 sm:gap-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="hidden md:inline text-[10px] uppercase font-bold text-stone-500 dark:text-gray-400">
                SORT:
              </span>
            </div>
            <select
              value={activeSort}
              onChange={(e) => {
                trackEvent("sort_order_changed", { sort: e.target.value });
                onSelectSort(e.target.value);
              }}
              className="w-full dark:bg-black/60 bg-stone-100 border dark:border-white/15 border-stone-300 rounded-xl pl-7 sm:pl-8 md:pl-20 pr-6 sm:pr-8 py-2 sm:py-2.5 dark:text-gray-200 text-stone-800 text-[11px] sm:text-xs font-mono focus:outline-none focus:border-[#e27d42] hover:border-[#e27d42]/50 cursor-pointer truncate shadow-sm transition-all appearance-none"
            >
              <option value="newest">LATEST / NEWEST</option>
              <option value="confidence">CONFIDENCE</option>
              <option value="researcher">RESEARCHER SCORE</option>
              <option value="engineer">ENGINEER SCORE</option>
              <option value="startup">STARTUP SCORE</option>
            </select>
            <div className="absolute right-2 sm:right-3 pointer-events-none text-stone-400 dark:text-gray-500 text-[9px] sm:text-[10px]">
              ▼
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
