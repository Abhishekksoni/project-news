"use client";

import React from "react";

export const OrbitaHero: React.FC = () => {
  return (
    <section className="relative w-full h-[50vh] flex flex-col justify-center items-center px-4 sm:px-6 lg:px-12 overflow-hidden text-center">
      {/* Cinematic Mars Surface Background Image */}
      <div className="absolute inset-0 z-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero.jpg"
          alt="Mars Aerospace Colony"
          className="w-full h-full object-cover object-center"
        />
        {/* Dark contrast overlays */}
        <div className="absolute inset-0 bg-black/15 backdrop-blur-[1px]" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#060305] via-transparent to-black/35" />
      </div>

      {/* Featured AI Quote on top of image */}
      <div className="relative z-10 max-w-3xl mx-auto px-4 space-y-3 sm:space-y-4">
        <blockquote className="font-['Rajdhani',sans-serif] text-lg sm:text-2xl md:text-3xl lg:text-[32px] font-bold text-white tracking-wide leading-snug drop-shadow-[0_4px_25px_rgba(0,0,0,0.95)]">
          &ldquo;By far, the greatest danger of Artificial Intelligence is that people conclude too early that they understand it.&rdquo;
        </blockquote>
      </div>

      {/* Clean bottom hairline divider */}
      <div className="absolute bottom-0 left-0 right-0 z-10">
        <div className="axis-hairline w-full" />
      </div>
    </section>
  );
};
