"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  TOOLS,
  CATEGORIES,
  type ToolCategory,
  type ToolItem,
} from "@/config/tools-list";

interface HomepageToolsGridProps {
  initialTools?: ToolItem[];
}

export function HomepageToolsGrid({ initialTools = TOOLS }: HomepageToolsGridProps) {
  const [activeCategory, setActiveCategory] = useState<ToolCategory>("all");

  const filteredTools = useMemo(() => {
    if (activeCategory === "all") return initialTools;
    return initialTools.filter((t) => t.category === activeCategory);
  }, [activeCategory, initialTools]);

  return (
    <div className="space-y-6">
      {/* Category Filter Pills & Counter */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 dark:border-gray-800/80 pb-4">
        <div
          className="flex flex-wrap items-center gap-2"
          role="tablist"
          aria-label="Filter PDF Tools by Category"
        >
          {CATEGORIES.map((cat) => {
            const isActive = activeCategory === cat.id;
            const count =
              cat.id === "all"
                ? initialTools.length
                : initialTools.filter((t) => t.category === cat.id).length;

            return (
              <button
                key={cat.id}
                role="tab"
                id={`homepage-tab-${cat.id}`}
                aria-selected={isActive}
                aria-controls="homepage-tools-list"
                onClick={() => setActiveCategory(cat.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
              >
                <span>{cat.label}</span>
                <span
                  className={`text-[11px] px-1.5 py-0.5 rounded-full font-bold ${
                    isActive
                      ? "bg-blue-700 text-blue-100"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="text-xs text-gray-500 dark:text-gray-400 font-medium">
          Showing <span className="font-bold text-gray-900 dark:text-gray-100">{filteredTools.length}</span> of {initialTools.length} tools
        </div>
      </div>

      {/* Tools Grid */}
      <div
        id="homepage-tools-list"
        role="region"
        aria-live="polite"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
      >
        {filteredTools.map((tool) => {
          const Icon = tool.icon;
          return (
            <Link
              key={tool.id}
              href={tool.href}
              id={`tool-card-${tool.id}`}
              data-testid={`homepage-tool-card-${tool.id}`}
              className="group block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-2xl"
            >
              <Card className="h-full flex flex-col justify-between border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-400 dark:hover:border-blue-600 hover:shadow-xl transition-all duration-200 group-hover:-translate-y-1">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between mb-3">
                    <div
                      className={`w-11 h-11 rounded-xl flex items-center justify-center shadow-md ${tool.colorClass} group-hover:scale-105 transition-transform duration-200`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
                      {tool.categoryLabel}
                    </span>
                  </div>
                  <CardTitle className="text-lg font-bold text-gray-900 dark:text-white flex items-center justify-between group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    <span>{tool.name}</span>
                    <ArrowRight className="w-4 h-4 text-blue-500 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all duration-200" />
                  </CardTitle>
                  <CardDescription className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed pt-1">
                    {tool.desc}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0 pb-4">
                  <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800/80 text-xs">
                    <span className="text-[11px] font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      {tool.badge}
                    </span>
                    <span className="text-[11px] text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-200 font-medium">
                      Open Tool &rarr;
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
