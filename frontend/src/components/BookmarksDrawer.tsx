"use client";

import React, { useState } from "react";
import {
  X,
  Globe,
  Microscope,
  Cpu,
  Rocket,
  ShieldAlert,
  Tv,
  Sun,
  Moon,
  ChevronRight,
  Filter,
} from "lucide-react";
import { StatsRecord } from "@/lib/db";
import { soundFX } from "@/lib/sounds";

interface BookmarksDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeRole: string;
  onSelectRole: (role: string) => void;
  theme?: "dark" | "light";
  onToggleTheme?: () => void;
  scanlinesEnabled?: boolean;
  setScanlinesEnabled?: (val: boolean) => void;
  stats?: StatsRecord | null;
  totalCount?: number;
}

export const BookmarksDrawer: React.FC<BookmarksDrawerProps> = ({
  isOpen,
  onClose,
  activeRole,
  onSelectRole,
  theme = "dark",
  onToggleTheme,
  scanlinesEnabled = false,
  setScanlinesEnabled,
  stats,
  totalCount = 0,
}) => {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);
  const isDark = theme === "dark";

  const roleCounts = stats?.roles || {
    ai_researcher: 0,
    ai_engineer: 0,
    startup_innovations: 0,
    noise: 0,
  };

  // Smooth right-to-left slide-in entrance and slide-out exit
  React.useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isOpen) {
      setMounted(true);
      timer = setTimeout(() => setVisible(true), 20);
    } else {
      setVisible(false);
      timer = setTimeout(() => setMounted(false), 300);
    }
    return () => clearTimeout(timer);
  }, [isOpen]);

  if (!mounted && !isOpen) return null;

  const handleClose = () => {
    soundFX.playBlip(400);
    onClose();
  };

  const roles = [
    {
      id: "all",
      name: "All Signal Streams",
      shortName: "ALL SIGNALS",
      icon: <Globe className="w-4 h-4 text-[#e27d42]" />,
      color: "text-[#e27d42]",
      activeBg: isDark ? "bg-[#e27d42]/20 border-[#e27d42]" : "bg-[#e27d42]/10 border-[#e27d42]",
      desc: "Unfiltered intelligence across all verified sources",
      count: totalCount || stats?.total || 0,
    },
    {
      id: "ai_researcher",
      name: "AI / ML Researcher",
      shortName: "RESEARCHER",
      icon: <Microscope className="w-4 h-4 text-cyan-400" />,
      color: "text-cyan-400",
      activeBg: isDark ? "bg-cyan-950/50 border-cyan-500" : "bg-cyan-100 border-cyan-400",
      desc: "arXiv & alphaXiv papers, models & benchmarks",
      count: roleCounts.ai_researcher || 0,
    },
    {
      id: "ai_engineer",
      name: "Software & AI Engineer",
      shortName: "AI ENGINEER",
      icon: <Cpu className="w-4 h-4 text-emerald-400" />,
      color: "text-emerald-400",
      activeBg: isDark ? "bg-emerald-950/50 border-emerald-500" : "bg-emerald-100 border-emerald-400",
      desc: "Tooling, SDKs, agent frameworks & fine-tuning",
      count: roleCounts.ai_engineer || 0,
    },
    {
      id: "startup_innovations",
      name: "Startups & Innovations",
      shortName: "STARTUPS & VENTURE",
      icon: <Rocket className="w-4 h-4 text-[#f59e0b]" />,
      color: "text-[#f59e0b]",
      activeBg: isDark ? "bg-[#e27d42]/30 border-[#e27d42]" : "bg-amber-100 border-amber-400",
      desc: "AI startup launches, VC rounds & commercial apps",
      count: roleCounts.startup_innovations || 0,
    },
    {
      id: "noise",
      name: "Noise Quarantine",
      shortName: "NOISE QUARANTINE",
      icon: <ShieldAlert className="w-4 h-4 text-purple-400" />,
      color: "text-purple-400",
      activeBg: isDark ? "bg-purple-950/50 border-purple-500" : "bg-purple-100 border-purple-400",
      desc: "Low-signal tech chatter & non-technical PR",
      count: roleCounts.noise || 0,
    },
  ];

  return (
    <div
      className={`fixed inset-0 z-50 flex justify-end bg-black/75 backdrop-blur-md transition-opacity duration-300 ease-out ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
      onClick={handleClose}
    >
      <div
        className={`w-full max-w-md h-full flex flex-col overflow-hidden transition-transform duration-300 ease-out shadow-2xl border-l transform ${
          visible ? "translate-x-0" : "translate-x-full"
        } ${
          isDark
            ? "bg-[#0b0609]/95 text-slate-100 border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.9)]"
            : "bg-[#faf7f2]/95 text-stone-900 border-stone-200 shadow-[0_0_50px_rgba(0,0,0,0.15)]"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header Bar */}
        <div className={`px-5 py-4 flex items-center justify-between border-b ${
          isDark ? "border-white/10 bg-[#120a10]" : "border-stone-200 bg-white"
        }`}>
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#e27d42] animate-pulse" />
            <div>
              <div className="font-['Orbitron',sans-serif] text-xs font-black tracking-widest uppercase flex items-center gap-1.5">
                <span>PROJECT NEWS</span>
                <span className="text-[#e27d42] text-[10px]">NAVIGATION</span>
              </div>
              <div className="font-mono text-[9px] text-stone-400 dark:text-gray-400 tracking-wider">
                ORBITAL MISSION CONTROL
              </div>
            </div>
          </div>

          <button
            onClick={handleClose}
            className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
              isDark
                ? "bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border-white/10"
                : "bg-stone-100 hover:bg-stone-200 text-stone-600 hover:text-stone-900 border-stone-300"
            }`}
            title="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6 font-mono text-xs">
          {/* Section 1: Role Switcher */}
          <div>
            <div className="flex items-center gap-1.5 text-[10px] uppercase text-stone-400 dark:text-gray-400 tracking-wider font-bold mb-3">
              <Filter className="w-3.5 h-3.5 text-[#e27d42]" />
              <span>SELECT INTELLIGENCE STREAM</span>
            </div>

            <div className="space-y-2">
              {roles.map((r) => {
                const isActive = activeRole === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => {
                      soundFX.playBlip(isActive ? 500 : 780);
                      onSelectRole(r.id);
                      handleClose();
                    }}
                    className={`w-full p-3.5 rounded-xl border flex items-center justify-between text-left transition-all cursor-pointer ${
                      isActive
                        ? `${r.activeBg} font-bold shadow-md`
                        : isDark
                        ? "bg-white/5 hover:bg-white/10 border-white/10 text-gray-300 hover:text-white"
                        : "bg-white hover:bg-stone-100 border-stone-200 text-stone-700 hover:text-stone-950 shadow-xs"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`p-2 rounded-lg ${isDark ? "bg-black/50" : "bg-stone-100"}`}>
                        {r.icon}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold font-['Rajdhani',sans-serif] tracking-wider uppercase ${r.color}`}>
                            {r.shortName}
                          </span>
                          {isActive && (
                            <span className="w-1.5 h-1.5 rounded-full bg-[#e27d42] animate-ping" />
                          )}
                        </div>
                        <div className="text-[10px] text-stone-400 font-sans truncate">
                          {r.desc}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isDark ? "bg-black/60 text-gray-300 border border-white/10" : "bg-stone-100 text-stone-700 border border-stone-300"
                      }`}>
                        {r.count}
                      </span>
                      <ChevronRight className={`w-4 h-4 ${isActive ? "text-[#e27d42]" : "text-stone-500 opacity-50"}`} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: Display & System Controls */}
          <div className="pt-4 border-t border-stone-200 dark:border-white/10 space-y-3">
            <div className="text-[10px] uppercase text-stone-400 dark:text-gray-400 tracking-wider font-bold">
              DISPLAY CONTROLS
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  soundFX.playBlip(800);
                  if (onToggleTheme) onToggleTheme();
                }}
                className={`p-3 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  isDark
                    ? "bg-white/5 hover:bg-white/10 border-white/10 text-white"
                    : "bg-white hover:bg-stone-100 border-stone-200 text-stone-900 shadow-xs"
                }`}
              >
                <div className="flex items-center gap-2">
                  {isDark ? <Sun className="w-4 h-4 text-[#f59e0b]" /> : <Moon className="w-4 h-4 text-stone-700" />}
                  <span>{isDark ? "LIGHT MODE" : "DARK MODE"}</span>
                </div>
              </button>

              <button
                onClick={() => {
                  soundFX.playBlip(800);
                  if (setScanlinesEnabled) setScanlinesEnabled(!scanlinesEnabled);
                }}
                className={`p-3 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  scanlinesEnabled
                    ? "bg-[#e27d42]/20 border-[#e27d42] text-[#e27d42]"
                    : isDark
                    ? "bg-white/5 hover:bg-white/10 border-white/10 text-white"
                    : "bg-white hover:bg-stone-100 border-stone-200 text-stone-900 shadow-xs"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Tv className="w-4 h-4 text-[#e27d42]" />
                  <span>CRT HUD</span>
                </div>
                <span className={`text-[9px] font-bold ${scanlinesEnabled ? "text-[#e27d42]" : "text-stone-500"}`}>
                  {scanlinesEnabled ? "ON" : "OFF"}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className={`p-4 border-t text-center font-mono text-[9px] text-stone-400 dark:text-gray-500 ${
          isDark ? "border-white/10 bg-[#0e070d]" : "border-stone-200 bg-stone-50"
        }`}>
          PROJECT NEWS // AUTONOMOUS AI RADAR
        </div>
      </div>
    </div>
  );
};
