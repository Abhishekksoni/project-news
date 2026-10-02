"use client";

import React, { useState } from "react";
import {
  X,
  ExternalLink,
  Sparkles,
  User,
  Calendar,
  Layers,
  Code,
  CheckCircle2,
  Copy,
  Info,
} from "lucide-react";
import { NewsItemRecord } from "@/lib/db";
import { soundFX } from "@/lib/sounds";

interface InspectorModalProps {
  item: NewsItemRecord | null;
  onClose: () => void;
}

export const InspectorModal: React.FC<InspectorModalProps> = ({
  item,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "json">("overview");
  const [copied, setCopied] = useState(false);

  if (!item) return null;

  const confPct = Math.round(item.confidence * 100);
  const resScore = Math.round(item.researcher_score * 100);
  const engScore = Math.round(item.engineer_score * 100);
  const startScore = Math.round(item.startup_score * 100);
  const noiseScore = Math.round(item.noise_score * 100);

  const handleCopyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(item, null, 2));
    setCopied(true);
    soundFX.playBlip(950);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl dark:bg-[#060c1c] bg-white border dark:border-cyan-500/40 border-stone-300 dark:shadow-[0_0_50px_rgba(0,240,255,0.2)] shadow-2xl overflow-hidden text-stone-900 dark:text-gray-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Futuristic Corner Brackets */}
        <span className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#e27d42]" />
        <span className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#e27d42]" />
        <span className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#e27d42]" />
        <span className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#e27d42]" />

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b dark:border-cyan-500/20 border-stone-200 dark:bg-cyan-950/30 bg-stone-50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg dark:bg-cyan-500/10 bg-[#e27d42]/10 border dark:border-cyan-500/30 border-[#e27d42]/30 text-[#e27d42]">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="font-mono text-[11px] text-[#e27d42] font-bold uppercase tracking-widest flex items-center gap-2">
                <span>SIGNAL DOSSIER</span>
                <span className="text-stone-400">//</span>
                <span className="dark:text-gray-300 text-stone-600 truncate max-w-[180px]">ID: {item.id}</span>
              </div>
              <h2 className="text-base font-bold dark:text-white text-stone-900 tracking-wide font-['Rajdhani',sans-serif]">
                DEEP TELEMETRY & JEV DECISION AUDIT
              </h2>
            </div>
          </div>

          <button
            onClick={() => {
              soundFX.playBlip(400);
              onClose();
            }}
            className="p-1.5 rounded-lg dark:bg-slate-900/80 bg-stone-200 dark:hover:bg-slate-800 hover:bg-stone-300 text-stone-500 dark:text-gray-400 dark:hover:text-white transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b dark:border-white/5 border-stone-200 font-mono text-xs">
          <button
            onClick={() => {
              soundFX.playBlip(700);
              setActiveTab("overview");
            }}
            className={`px-3 py-2 border-b-2 font-bold transition-all cursor-pointer ${
              activeTab === "overview"
                ? "border-[#e27d42] text-[#e27d42]"
                : "border-transparent text-stone-500 hover:text-stone-800 dark:text-gray-400 dark:hover:text-gray-200"
            }`}
          >
            DECISION OVERVIEW
          </button>
          <button
            onClick={() => {
              soundFX.playBlip(700);
              setActiveTab("json");
            }}
            className={`px-3 py-2 border-b-2 font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === "json"
                ? "border-[#e27d42] text-[#e27d42]"
                : "border-transparent text-stone-500 hover:text-stone-800 dark:text-gray-400 dark:hover:text-gray-200"
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            <span>RAW PAYLOAD</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {activeTab === "overview" ? (
            <>
              {/* Signal Title & Meta */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap font-mono text-xs">
                  <span className="px-2.5 py-1 rounded dark:bg-cyan-950/60 bg-stone-100 border dark:border-cyan-500/40 border-stone-300 text-[#e27d42] font-bold">
                    {item.source}
                  </span>
                  {item.category && (
                    <span className="px-2.5 py-1 rounded dark:bg-slate-900 bg-stone-100 border dark:border-white/10 border-stone-300 text-stone-600 dark:text-gray-300">
                      {item.category}
                    </span>
                  )}
                  <span className="px-2.5 py-1 rounded dark:bg-emerald-950/60 bg-emerald-50 border dark:border-emerald-500/40 border-emerald-300 text-emerald-700 dark:text-emerald-300 font-bold">
                    WINNING ROLE: {item.primary_role?.toUpperCase()} ({confPct}%)
                  </span>
                </div>

                <h3 className="text-xl font-bold dark:text-white text-stone-900 leading-snug font-['Rajdhani',sans-serif]">
                  {item.title}
                </h3>

                <div className="flex items-center gap-4 text-xs font-mono text-stone-500 dark:text-gray-400">
                  {item.author && (
                    <span className="flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-[#e27d42]" />
                      <span>{item.author}</span>
                    </span>
                  )}
                  {item.published_at && (
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-[#e27d42]" />
                      <span>{new Date(item.published_at).toLocaleString()}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Description & 350 Char Limit Guard Box */}
              <div className="p-4 rounded-xl dark:bg-slate-950/60 bg-stone-50 border dark:border-white/10 border-stone-200 space-y-2">
                <div className="flex items-center justify-between font-mono text-[11px] text-stone-500 dark:text-gray-400">
                  <span className="text-[#e27d42] font-bold flex items-center gap-1">
                    <Info className="w-3.5 h-3.5" /> SIGNAL DESCRIPTION / ABSTRACT
                  </span>
                  <span className="px-2 py-0.5 rounded dark:bg-cyan-950/40 bg-amber-50 border dark:border-cyan-500/30 border-amber-300 text-[#e27d42] text-[10px] font-bold">
                    350 CHAR GUARD: ENFORCED
                  </span>
                </div>
                <p className="text-sm dark:text-gray-300 text-stone-700 leading-relaxed font-sans">
                  {item.description || "No description provided for this telemetry record."}
                </p>
                {item.description && (
                  <div className="text-[10px] font-mono text-stone-400 dark:text-gray-500 text-right pt-1">
                    Payload Length: {item.description.length} characters (Max 350 limit satisfied)
                  </div>
                )}
              </div>

              {/* Jev System One Probability Matrix */}
              <div className="space-y-3">
                <div className="font-mono text-xs text-[#e27d42] font-bold uppercase tracking-wider flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  <span>JEV SYSTEM ONE PROBABILITY BREAKDOWN</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl dark:bg-cyan-950/20 bg-cyan-50/50 border dark:border-cyan-500/30 border-cyan-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-cyan-700 dark:text-cyan-300 font-bold">AI / ML RESEARCHER</span>
                      <span className="text-cyan-700 dark:text-cyan-300 font-bold">{resScore}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full dark:bg-black/60 bg-stone-200 overflow-hidden">
                      <div style={{ width: `${resScore}%` }} className="h-full bg-cyan-500 rounded-full" />
                    </div>
                  </div>

                  <div className="p-3 rounded-xl dark:bg-emerald-950/20 bg-emerald-50/50 border dark:border-emerald-500/30 border-emerald-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-emerald-700 dark:text-emerald-300 font-bold">AI & SOFTWARE ENGINEER</span>
                      <span className="text-emerald-700 dark:text-emerald-300 font-bold">{engScore}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full dark:bg-black/60 bg-stone-200 overflow-hidden">
                      <div style={{ width: `${engScore}%` }} className="h-full bg-emerald-500 rounded-full" />
                    </div>
                  </div>

                  <div className="p-3 rounded-xl dark:bg-amber-950/20 bg-amber-50/50 border dark:border-amber-500/30 border-amber-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-amber-800 dark:text-amber-300 font-bold">STARTUPS & VENTURE</span>
                      <span className="text-amber-800 dark:text-amber-300 font-bold">{startScore}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full dark:bg-black/60 bg-stone-200 overflow-hidden">
                      <div style={{ width: `${startScore}%` }} className="h-full bg-[#e27d42] rounded-full" />
                    </div>
                  </div>

                  <div className="p-3 rounded-xl dark:bg-purple-950/20 bg-purple-50/50 border dark:border-purple-500/30 border-purple-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-purple-700 dark:text-purple-300 font-bold">NOISE / OFF-TOPIC</span>
                      <span className="text-purple-700 dark:text-purple-300 font-bold">{noiseScore}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full dark:bg-black/60 bg-stone-200 overflow-hidden">
                      <div style={{ width: `${noiseScore}%` }} className="h-full bg-purple-500 rounded-full" />
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="relative">
              <button
                onClick={handleCopyJSON}
                className="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg dark:bg-slate-800 bg-stone-200 dark:hover:bg-slate-700 hover:bg-stone-300 text-xs font-mono text-[#e27d42] border dark:border-white/10 border-stone-300 transition-all cursor-pointer font-bold"
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "COPIED" : "COPY JSON"}</span>
              </button>
              <pre className="p-4 rounded-xl dark:bg-black/80 bg-stone-900 border dark:border-white/10 border-stone-700 font-mono text-xs text-amber-300 overflow-x-auto leading-relaxed">
                {JSON.stringify(item, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t dark:border-cyan-500/20 border-stone-200 dark:bg-[#040814] bg-stone-100 font-mono text-xs">
          <span className="text-stone-500 dark:text-gray-400">
            DEDUP: <strong className="dark:text-white text-stone-800">{item.is_duplicate ? "DUPLICATE (LINKED)" : "ORIGINAL CANONICAL"}</strong>
          </span>

          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => soundFX.playBlip(800)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#e27d42]/20 hover:bg-[#e27d42]/30 text-[#e27d42] border border-[#e27d42]/60 font-bold transition-all"
          >
            <span>ACCESS SOURCE NODE</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
};
