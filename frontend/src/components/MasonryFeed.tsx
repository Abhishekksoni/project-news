"use client";

import React, { useState, useEffect } from "react";
import { NewsItemRecord } from "@/lib/db";
import { NewsCard } from "@/components/NewsCard";

interface MasonryFeedProps {
  items: NewsItemRecord[];
  onInspect?: (item: NewsItemRecord) => void;
}

export const MasonryFeed: React.FC<MasonryFeedProps> = ({
  items,
  onInspect,
}) => {
  const [cols, setCols] = useState<number>(4);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
    const updateCols = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setCols(2);
      } else if (width < 1280) {
        setCols(3);
      } else {
        setCols(4);
      }
    };

    updateCols();
    window.addEventListener("resize", updateCols);
    return () => window.removeEventListener("resize", updateCols);
  }, []);

  const columnCount = mounted ? cols : 4;
  const columns: NewsItemRecord[][] = Array.from({ length: columnCount }, () => []);
  items.forEach((item, index) => {
    columns[index % columnCount].push(item);
  });

  return (
    <div
      className="grid gap-3 sm:gap-5 lg:gap-6 items-start w-full"
      style={{
        gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
      }}
    >
      {columns.map((colItems, colIdx) => (
        <div key={colIdx} className="flex flex-col gap-3 sm:gap-5 lg:gap-6 w-full min-w-0">
          {colItems.map((item) => (
            <NewsCard
              key={item.id}
              item={item}
              onInspect={onInspect}
            />
          ))}
        </div>
      ))}
    </div>
  );
};
