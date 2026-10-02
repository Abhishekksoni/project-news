"use client";

import React, { useState, useRef } from "react";
import {
  Tv,
  Sparkles,
  Menu,
  Sun,
  Moon,
  Search,
  X,
} from "lucide-react";
import { soundFX } from "@/lib/sounds";

interface HeaderProps {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  scanlinesEnabled: boolean;
  setScanlinesEnabled: (val: boolean) => void;
  onOpenBookmarks: () => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  onToggleTheme,
  scanlinesEnabled,
  setScanlinesEnabled,
  onOpenBookmarks,
  searchQuery = "",
  onSearchChange,
}) => {
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const isDark = theme === "dark";

  const toggleSearch = () => {
    soundFX.playBlip(750);
    if (!isSearchExpanded) {
      setIsSearchExpanded(true);
      setTimeout(() => searchInputRef.current?.focus(), 80);
    } else {
      if (!searchQuery) {
        setIsSearchExpanded(false);
      }
    }
  };

  return (
    <header className={`sticky top-0 z-50 w-full px-3.5 sm:px-6 lg:px-12 py-3.5 sm:py-4 transition-all duration-300 backdrop-blur-md ${
      isDark
        ? "bg-gradient-to-b from-[#070406] via-[#070406]/95 to-transparent text-white"
        : "bg-gradient-to-b from-[#f6f2ec] via-[#f6f2ec]/95 to-transparent text-stone-900"
    }`}>
      <div className="max-w-[1600px] mx-auto flex items-center justify-between gap-2">
        {/* Left: Project News Brand Logo */}
        <div className="flex items-center gap-2 sm:gap-4 min-w-0">
          <a
            href="/"
            className="group flex items-baseline gap-1.5 sm:gap-2 cursor-pointer truncate"
          >
            <span className="font-['Orbitron',sans-serif] text-base sm:text-xl md:text-2xl lg:text-3xl font-black tracking-[0.1em] sm:tracking-[0.15em] transition-colors group-hover:text-[#e27d42] truncate">
              PROJECT NEWS
            </span>
            <span className="text-[10px] sm:text-xs font-mono font-normal text-[#e27d42] tracking-widest uppercase flex-shrink-0">
              ®
            </span>
          </a>
        </div>

        {/* Right Controls: Expandable Search, Console, Theme, CRT HUD, & Hamburger */}
        <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
          {/* Expandable Search Input / Icon Button */}
          {onSearchChange && (
            <div className="relative flex items-center">
              {isSearchExpanded || (searchQuery && searchQuery.length > 0) ? (
                <div className="relative flex items-center animate-in fade-in duration-200">
                  <Search className="absolute left-2.5 sm:left-3 w-3.5 h-3.5 text-[#e27d42] pointer-events-none" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => onSearchChange(e.target.value)}
                    placeholder="Search signals..."
                    className={`w-32 xs:w-44 sm:w-60 md:w-72 pl-8 pr-7 py-1.5 rounded-xl text-xs font-mono transition-all border outline-none ${
                      isDark
                        ? "bg-black/90 text-white placeholder-gray-500 border-white/20 focus:border-[#e27d42] shadow-[0_0_15px_rgba(0,0,0,0.8)]"
                        : "bg-white text-stone-900 placeholder-stone-400 border-stone-300 focus:border-[#e27d42] shadow-xs"
                    }`}
                  />
                  <button
                    onClick={() => {
                      if (searchQuery) {
                        onSearchChange("");
                      } else {
                        setIsSearchExpanded(false);
                      }
                    }}
                    className="absolute right-2 text-stone-400 hover:text-stone-200 cursor-pointer p-0.5"
                    title="Close search"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={toggleSearch}
                  className={`p-1.5 sm:p-2 rounded-xl border transition-all cursor-pointer ${
                    isDark
                      ? "bg-white/5 hover:bg-white/10 text-gray-300 hover:text-[#e27d42] border-white/10 hover:border-[#e27d42]/50"
                      : "bg-white hover:bg-stone-100 text-stone-700 hover:text-[#e27d42] border-stone-300 hover:border-[#e27d42]/50 shadow-xs"
                  }`}
                  title="Search signals"
                >
                  <Search className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#e27d42]" />
                </button>
              )}
            </div>
          )}

          {/* Quick Controls: Light/Dark Theme & Scanline */}
          <div className={`flex items-center gap-1 pl-1.5 sm:pl-2.5 ${
            isDark ? "border-white/10" : "border-stone-300"
          }`}>
            {/* Theme Toggle Button */}
            <button
              onClick={onToggleTheme}
              title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
              className={`p-1.5 sm:p-2 rounded-lg transition-all cursor-pointer ${
                isDark
                  ? "bg-white/5 hover:bg-white/10 text-[#f59e0b] hover:text-[#fbbf24] border border-white/10"
                  : "bg-stone-200/80 hover:bg-stone-300 text-stone-800 border border-stone-300"
              }`}
            >
              {isDark ? <Sun className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Moon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
            </button>

            {/* CRT HUD Toggle (Hidden on smaller screens) */}
            <button
              onClick={() => setScanlinesEnabled(!scanlinesEnabled)}
              title="Toggle CRT Scanline HUD"
              className={`hidden sm:inline-flex items-center justify-center p-1.5 sm:p-2 rounded-lg transition-all cursor-pointer ${
                scanlinesEnabled
                  ? "text-[#e27d42] bg-[#e27d42]/10 border border-[#e27d42]/40"
                  : isDark ? "text-gray-500 hover:text-gray-300" : "text-stone-400 hover:text-stone-700"
              }`}
            >
              <Tv className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </button>
          </div>

          {/* Mission Navigation Hamburger Trigger */}
          <button
            onClick={() => {
              soundFX.playModalOpen();
              onOpenBookmarks();
            }}
            className={`relative flex items-center justify-center p-2 rounded-xl transition-all cursor-pointer border ${
              isDark
                ? "bg-white/5 hover:bg-white/10 text-white border-white/10 hover:border-[#e27d42] hover:shadow-[0_0_15px_rgba(226,125,66,0.3)]"
                : "bg-white hover:bg-stone-100 text-stone-800 border-stone-300 hover:border-[#e27d42] shadow-xs hover:shadow-[0_0_15px_rgba(226,125,66,0.2)]"
            }`}
            title="Open Mission Navigation"
          >
            <Menu className="w-4 h-4 sm:w-5 sm:h-5 text-[#e27d42]" />
          </button>
        </div>
      </div>
    </header>
  );
};
