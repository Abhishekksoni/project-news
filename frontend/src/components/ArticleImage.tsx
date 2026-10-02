"use client";

import React, { useState } from "react";

interface ArticleImageProps {
  src: string | null;
  alt: string;
  role?: string | null;
  className?: string;
  onError?: () => void;
}

export const ArticleImage: React.FC<ArticleImageProps> = ({
  src,
  alt,
  className = "",
  onError,
}) => {
  const [hasError, setHasError] = useState(false);

  if (!src || src.trim().length === 0 || hasError) {
    return null;
  }

  return (
    <div className={`relative overflow-hidden bg-black/60 ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        onError={() => {
          setHasError(true);
          if (onError) onError();
        }}
        className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
        loading="lazy"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#090507] via-transparent to-transparent opacity-80" />
    </div>
  );
};

