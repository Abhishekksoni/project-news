"use client";

import React from "react";
import {
  Globe,
  Microscope,
  Cpu,
  Rocket,
  ShieldAlert,
} from "lucide-react";
import { soundFX } from "@/lib/sounds";

export interface RoleConfig {
  id: string;
  name: string;
  shortName: string;
  icon: React.ReactNode;
  color: string;
  borderColor: string;
  activeBg: string;
  desc: string;
}

export const ROLES: RoleConfig[] = [
  {
    id: "all",
    name: "All Signal Streams",
    shortName: "ALL SIGNALS",
    icon: <Globe className="w-4 h-4" />,
    color: "dark:text-white text-stone-800",
    borderColor: "border-[#e27d42]",
    activeBg: "dark:bg-[#e27d42]/20 bg-[#e27d42]/15",
    desc: "Unfiltered intelligence aggregated across all verified research, engineering & venture nodes.",
  },
  {
    id: "ai_researcher",
    name: "AI / ML Researcher",
    shortName: "RESEARCHER",
    icon: <Microscope className="w-4 h-4" />,
    color: "dark:text-cyan-400 text-cyan-600",
    borderColor: "border-cyan-500",
    activeBg: "dark:bg-cyan-950/40 bg-cyan-100",
    desc: "Theoretical advances, mathematical formulations, foundational models & alphaXiv papers.",
  },
  {
    id: "ai_engineer",
    name: "Software & AI Engineer",
    shortName: "AI ENGINEER",
    icon: <Cpu className="w-4 h-4" />,
    color: "dark:text-emerald-400 text-emerald-600",
    borderColor: "border-emerald-500",
    activeBg: "dark:bg-emerald-950/40 bg-emerald-100",
    desc: "Developer tooling, open-source repos, fine-tuning scripts, model checkpoints & infra.",
  },
  {
    id: "startup_innovations",
    name: "Startups & Innovations",
    shortName: "STARTUPS & VENTURE",
    icon: <Rocket className="w-4 h-4" />,
    color: "dark:text-[#f59e0b] text-amber-600",
    borderColor: "border-[#e27d42]",
    activeBg: "dark:bg-[#e27d42]/30 bg-amber-100",
    desc: "New AI startups, product rollouts, VC funding rounds, commercial apps & market disruptions.",
  },
  {
    id: "noise",
    name: "Noise & Off-Topic Filter",
    shortName: "NOISE QUARANTINE",
    icon: <ShieldAlert className="w-4 h-4" />,
    color: "dark:text-purple-400 text-purple-600",
    borderColor: "border-purple-500",
    activeBg: "dark:bg-purple-950/40 bg-purple-100",
    desc: "General tech chatter, generic crypto PR, political buzz, and non-AI posts detected by Jev.",
  },
];

interface RoleFiltersProps {
  activeRole: string;
  onSelectRole: (role: string) => void;
  counts?: Record<string, number>;
  totalCount?: number;
}

export const RoleFilters: React.FC<RoleFiltersProps> = ({
  activeRole,
  onSelectRole,
  counts = {},
  totalCount = 0,
}) => {
  return (
    <div className="w-full">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {ROLES.map((role) => {
          const isActive = activeRole === role.id;
          const count = role.id === "all" ? totalCount : counts[role.id] || 0;

          return (
            <button
              key={role.id}
              onClick={() => {
                soundFX.playBlip(isActive ? 500 : 780);
                onSelectRole(role.id);
              }}
              className={`relative flex flex-col p-4 rounded-xl border text-left transition-all duration-300 cursor-pointer overflow-hidden shadow-sm ${
                isActive
                  ? `${role.activeBg} ${role.borderColor} dark:text-white text-stone-900 shadow-[0_0_20px_rgba(226,125,66,0.15)]`
                  : "dark:bg-[#0c0609]/80 bg-white/80 dark:border-white/10 border-stone-200 hover:border-[#e27d42]/50 hover:bg-stone-50 dark:hover:bg-[#12090e] dark:text-gray-400 text-stone-600"
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <div className={`p-2 rounded-lg ${isActive ? "dark:bg-white/15 bg-black/5" : "dark:bg-white/5 bg-black/5"} ${role.color}`}>
                  {role.icon}
                </div>
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded-full dark:bg-black/60 bg-stone-100 dark:border-white/10 border-stone-300 dark:text-gray-300 text-stone-700">
                  {count}
                </span>
              </div>

              <div className="font-['Rajdhani',sans-serif] text-sm font-bold tracking-wider uppercase dark:text-white text-stone-900 truncate">
                {role.shortName}
              </div>
              <div className="text-[11px] dark:text-gray-400 text-stone-500 line-clamp-1 mt-0.5 font-mono">
                {role.name}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
