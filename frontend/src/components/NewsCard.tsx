"use client";

import React from "react";
import {
  ExternalLink,
  Bookmark,
  Sparkles,
  Clock,
  Globe,
  Box,
  GitBranch,
  Microscope,
  Cpu,
  Rocket,
  ShieldAlert,
  Activity,
} from "lucide-react";
import { NewsItemRecord } from "@/lib/db";
import { ArticleImage } from "@/components/ArticleImage";
import { soundFX } from "@/lib/sounds";
import { trackEvent } from "@/app/providers";

interface NewsCardProps {
  item: NewsItemRecord;
  onInspect?: (item: NewsItemRecord) => void;
}

const getSourceDomain = (source: string, url?: string): string => {
  if (url) {
    try {
      return new URL(url).hostname;
    } catch {
      // fallback
    }
  }
  const s = source.toLowerCase();
  if (s.includes("openai")) return "openai.com";
  if (s.includes("hacker") || s.includes("hn") || s.includes("ycombinator")) return "news.ycombinator.com";
  if (s.includes("techcrunch")) return "techcrunch.com";
  if (s.includes("towards") || s.includes("tds")) return "towardsdatascience.com";
  if (s.includes("hugging")) return "huggingface.co";
  if (s.includes("github")) return "github.com";
  if (s.includes("alphaxiv") || s.includes("arxiv")) return "arxiv.org";
  if (s.includes("mit")) return "technologyreview.com";
  if (s.includes("venturebeat")) return "venturebeat.com";
  if (s.includes("anthropic")) return "anthropic.com";
  if (s.includes("google") || s.includes("deepmind")) return "deepmind.google";
  if (s.includes("meta")) return "ai.meta.com";
  return "google.com";
};

export const SourceLogo: React.FC<{ source: string; url?: string; className?: string }> = ({
  source,
  url,
  className = "",
}) => {
  const domain = getSourceDomain(source, url);
  const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  const [error, setError] = React.useState(false);

  return (
    <div className={`w-4 h-4 rounded-md overflow-hidden bg-stone-100 dark:bg-white/10 p-0.5 border border-stone-200 dark:border-white/10 flex items-center justify-center flex-shrink-0 shadow-xs ${className}`}>
      {!error ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={faviconUrl}
          alt={source}
          onError={() => setError(true)}
          className="w-full h-full object-contain rounded-xs"
          loading="lazy"
        />
      ) : (
        <Globe className="w-2.5 h-2.5 text-[#e27d42]" />
      )}
    </div>
  );
};

export const NewsCard: React.FC<NewsCardProps> = ({
  item,
}) => {
  const isModelHub = item.source === "Hugging Face Model Hub" || item.source_type === "model_hub";
  const isGithubRepo = item.source.toLowerCase().includes("github") || item.source_type === "github_repo";

  const getRoleConfig = (role: string | null) => {
    if (isModelHub) {
      return {
        label: "HF MODEL",
        icon: <Box className="w-3 h-3 text-[#f59e0b] flex-shrink-0" />,
        badge: "dark:bg-amber-950/90 bg-amber-100 text-amber-800 dark:text-[#f59e0b] border-[#e27d42]/70 dark:border-[#e27d42]/80 shadow-[0_0_12px_rgba(226,125,66,0.25)]",
        barColor: "bg-[#e27d42]",
      };
    }
    if (isGithubRepo) {
      return {
        label: "GITHUB REPO",
        icon: <GitBranch className="w-3 h-3 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />,
        badge: "dark:bg-emerald-950/90 bg-emerald-100 text-emerald-800 dark:text-emerald-300 border-emerald-500/60 dark:border-emerald-400/70 shadow-[0_0_12px_rgba(16,185,129,0.25)]",
        barColor: "bg-emerald-500",
      };
    }
    switch (role) {
      case "ai_researcher":
        return {
          label: "RESEARCHER",
          icon: <Microscope className="w-3 h-3 text-cyan-600 dark:text-cyan-400 flex-shrink-0" />,
          badge: "dark:bg-cyan-950/90 bg-cyan-100 text-cyan-800 dark:text-cyan-300 border-cyan-500/60 dark:border-cyan-400/70 shadow-[0_0_12px_rgba(6,182,212,0.25)]",
          barColor: "bg-cyan-500",
        };
      case "ai_engineer":
        return {
          label: "AI ENGINEER",
          icon: <Cpu className="w-3 h-3 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />,
          badge: "dark:bg-emerald-950/90 bg-emerald-100 text-emerald-800 dark:text-emerald-300 border-emerald-500/60 dark:border-emerald-400/70 shadow-[0_0_12px_rgba(16,185,129,0.25)]",
          barColor: "bg-emerald-500",
        };
      case "startup_innovations":
        return {
          label: "STARTUPS",
          icon: <Rocket className="w-3 h-3 text-[#c25e24] dark:text-[#f59e0b] flex-shrink-0" />,
          badge: "dark:bg-amber-950/90 bg-amber-100 text-amber-800 dark:text-[#f59e0b] border-[#e27d42]/70 dark:border-[#e27d42]/80 shadow-[0_0_12px_rgba(226,125,66,0.25)]",
          barColor: "bg-[#e27d42]",
        };
      case "noise":
        return {
          label: "NOISE",
          icon: <ShieldAlert className="w-3 h-3 text-purple-600 dark:text-purple-400 flex-shrink-0" />,
          badge: "dark:bg-purple-950/90 bg-purple-100 text-purple-800 dark:text-purple-300 border-purple-500/60 dark:border-purple-400/70 shadow-[0_0_12px_rgba(168,85,247,0.25)]",
          barColor: "bg-purple-500",
        };
      default:
        return {
          label: "SIGNAL",
          icon: <Activity className="w-3 h-3 text-stone-500 dark:text-gray-400 flex-shrink-0" />,
          badge: "dark:bg-white/10 bg-stone-100 text-stone-800 dark:text-gray-300 border-stone-300 dark:border-white/20 shadow-sm",
          barColor: "bg-stone-400",
        };
    }
  };

  const roleStyle = getRoleConfig(item.primary_role);
  const confPct = Math.round(item.confidence * 100);

  const resScore = Math.round(item.researcher_score * 100);
  const engScore = Math.round(item.engineer_score * 100);
  const startScore = Math.round(item.startup_score * 100);
  const noiseScore = Math.round(item.noise_score * 100);

  const [imgError, setImgError] = React.useState(false);
  const hasImage = Boolean(item.image_url && item.image_url.trim().length > 0 && !imgError);

  const dateToFormat = item.published_at || item.collected_at;
  const formattedDate = dateToFormat
    ? new Date(dateToFormat).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "RECENT";

  return (
    <div
      onClick={() => {
        soundFX.playBlip(750);
        trackEvent("article_clicked", {
          id: item.id,
          title: item.title,
          source: item.source,
          role: item.primary_role,
          url: item.url,
        });
        window.open(item.url, "_blank", "noopener,noreferrer");
      }}
      className="group relative w-full flex flex-col justify-between rounded-xl sm:rounded-2xl dark:bg-[#0c070a] bg-white border dark:border-white/10 border-stone-200/90 dark:hover:border-[#e27d42]/60 hover:border-[#e27d42] dark:hover:shadow-[0_20px_40px_-10px_rgba(0,0,0,0.9),0_0_25px_-5px_rgba(226,125,66,0.25)] hover:shadow-[0_20px_35px_-10px_rgba(226,125,66,0.15),0_0_15px_rgba(0,0,0,0.05)] transition-all duration-300 cursor-pointer overflow-hidden backdrop-blur-xl shadow-sm"
    >
      {/* Top Image Container - ONLY rendered when a valid real article image is present */}
      {hasImage && (
        <div className="relative w-full aspect-[16/10] overflow-hidden bg-stone-900">
          <ArticleImage
            src={item.image_url}
            alt={item.title}
            onError={() => setImgError(true)}
            className="w-full h-full"
          />

          {/* Floating Source & Role Badges (Always Visible on Image) */}
          <div className="absolute top-2 left-2 right-2 sm:top-3 sm:left-3 sm:right-3 flex items-center justify-between gap-1.5 z-10 pointer-events-none">
            <span className="p-1 sm:px-2.5 sm:py-1 rounded-full bg-black/80 backdrop-blur-md border border-white/20 text-white font-mono text-[9px] sm:text-[10px] font-bold tracking-wider uppercase shadow-md flex items-center gap-1.5 flex-shrink-0">
              <SourceLogo source={item.source} url={item.url} className="w-3.5 h-3.5 border-0 bg-transparent p-0" />
              <span className="truncate hidden sm:inline max-w-[140px]">{item.source}</span>
            </span>

            <span className={`px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full backdrop-blur-md border font-mono text-[9px] sm:text-[10px] font-bold tracking-wider uppercase flex items-center gap-1.5 shadow-lg ${roleStyle.badge}`}>
              {roleStyle.icon}
              <span className="truncate max-w-[75px] sm:max-w-none">{roleStyle.label}</span>
              {!isModelHub && !isGithubRepo && (
                <span className="opacity-80 hidden sm:inline">[{confPct}%]</span>
              )}
            </span>
          </div>

          {/* Quick Hover Action Bar */}
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2 z-20">
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                e.stopPropagation();
                soundFX.playBlip(700);
              }}
              title="Open Original Source"
              className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-black/85 hover:bg-black text-white border border-white/30 font-mono text-[11px] sm:text-xs font-bold transition-all transform hover:scale-105 shadow-lg"
            >
              <span>{isModelHub ? "VIEW MODEL" : isGithubRepo ? "VIEW REPO" : "READ ARTICLE"}</span>
              <ExternalLink className="w-3.5 h-3.5 text-[#f59e0b]" />
            </a>
          </div>
        </div>
      )}

      {/* Card Body with Responsive Spacing */}
      <div className="p-3 sm:p-4 lg:p-5 space-y-2.5 sm:space-y-3.5">
        {/* If card has NO image, show top badge row directly in card header */}
        {!hasImage && (
          <div className="flex items-center justify-between gap-2 pb-1">
            <span className="p-1 sm:px-2 py-0.5 rounded-full dark:bg-white/5 bg-black/5 dark:border-white/10 border-stone-200 border font-mono text-[9px] sm:text-[10px] font-bold tracking-wider uppercase flex items-center gap-1.5 dark:text-gray-300 text-stone-700">
              <SourceLogo source={item.source} url={item.url} className="w-3.5 h-3.5" />
              <span className="truncate hidden sm:inline max-w-[140px]">{item.source}</span>
            </span>

            <span className={`px-2 sm:px-2.5 py-0.5 rounded-full border font-mono text-[9px] sm:text-[10px] font-bold tracking-wider uppercase flex items-center gap-1.5 shadow-sm ${roleStyle.badge}`}>
              {roleStyle.icon}
              <span className="truncate max-w-[75px] sm:max-w-none">{roleStyle.label}</span>
              {!isModelHub && !isGithubRepo && (
                <span className="opacity-80 hidden sm:inline">[{confPct}%]</span>
              )}
            </span>
          </div>
        )}

        {/* Title */}
        <h3 className="font-['Rajdhani',sans-serif] text-sm sm:text-base lg:text-lg font-bold dark:text-white text-stone-900 group-hover:text-[#c25e24] dark:group-hover:text-[#f59e0b] transition-colors line-clamp-2 sm:line-clamp-3 leading-tight sm:leading-snug">
          {item.title}
        </h3>

        {/* Description Snippet: expanded and readable */}
        {item.description && (
          <p className="text-xs sm:text-[13px] dark:text-stone-300 text-stone-700 font-sans leading-relaxed line-clamp-4 sm:line-clamp-5">
            {item.description}
          </p>
        )}

        {/* Model Hub / GitHub Repo subtle indicator (if applicable) */}
        {isModelHub ? (
          <div className="pt-2 border-t dark:border-white/5 border-stone-200">
            <div className="flex items-center justify-between font-mono text-[9px] dark:text-[#f59e0b] text-amber-800 dark:bg-[#e27d42]/10 bg-amber-50/80 px-2.5 py-1 rounded-lg border dark:border-[#e27d42]/20 border-amber-200">
              <span className="flex items-center gap-1.5 font-bold">
                <Box className="w-3.5 h-3.5 text-[#e27d42]" /> MODEL HUB ARTIFACT
              </span>
              <span className="text-[8px] uppercase font-mono tracking-wider opacity-90">CHECKPOINTS</span>
            </div>
          </div>
        ) : isGithubRepo ? (
          <div className="pt-2 border-t dark:border-white/5 border-stone-200">
            <div className="flex items-center justify-between font-mono text-[9px] dark:text-emerald-400 text-emerald-800 dark:bg-emerald-950/30 bg-emerald-50/80 px-2.5 py-1 rounded-lg border dark:border-emerald-500/20 border-emerald-200">
              <span className="flex items-center gap-1.5 font-bold">
                <GitBranch className="w-3.5 h-3.5 text-emerald-500" /> OPEN SOURCE REPO
              </span>
              <span className="text-[8px] uppercase font-mono tracking-wider opacity-90">TRENDING CODE</span>
            </div>
          </div>
        ) : null}

        {/* Card Footer: Left Source Logo/Name | Right Corner Confidence & Date */}
        <div className="flex items-center justify-between pt-2 sm:pt-2.5 border-t dark:border-white/5 border-stone-200 font-mono text-[9px] sm:text-[10px] dark:text-gray-300 text-stone-600">
          {/* Bottom Left: Source Logo & Name */}
          <div className="flex items-center gap-1.5 truncate max-w-[170px]" title={item.source}>
            <SourceLogo source={item.source} url={item.url} />
            <span className="truncate font-bold tracking-wider uppercase">
              {item.source}
            </span>
          </div>

          {/* Bottom Right: Small Corner Confidence & Date */}
          <div className="flex items-center gap-2 text-stone-500 dark:text-gray-400 flex-shrink-0">
            {!isModelHub && !isGithubRepo && (
              <span className="hidden sm:inline-flex text-[#c25e24] dark:text-[#f59e0b] font-bold text-[9px] sm:text-[10px] items-center gap-0.5">
                <Sparkles className="w-2.5 h-2.5 text-[#e27d42]" />
                {confPct}%
              </span>
            )}
            <div className="flex items-center gap-1">
              <Clock className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-stone-400 dark:text-gray-500" />
              <span>{formattedDate}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
