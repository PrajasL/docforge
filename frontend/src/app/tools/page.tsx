"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Layers,
  Scissors,
  Minimize2,
  RotateCw,
  Stamp,
  Hash,
  Lock,
  Unlock,
  FileSpreadsheet,
  LayoutGrid,
  Image as ImageIcon,
  Search,
  X,
  ArrowRight,
  Sparkles,
  Shield,
  FileCheck,
  SlidersHorizontal,
  Wrench,
} from "lucide-react";

export type ToolCategory = "all" | "organize" | "optimize" | "convert" | "security";

interface ToolItem {
  id: string;
  name: string;
  desc: string;
  href: string;
  category: ToolCategory;
  categoryLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
  badge: string;
  keywords: string[];
}

export const TOOLS: ToolItem[] = [
  {
    id: "merge-pdf",
    name: "Merge PDF",
    desc: "Combine multiple PDF documents into a single unified file in your exact custom order.",
    href: "/merge",
    category: "organize",
    categoryLabel: "Organize",
    icon: Layers,
    colorClass: "bg-blue-600 text-white shadow-blue-500/20",
    badge: "Most Popular",
    keywords: ["merge", "combine", "join", "concatenate", "unify", "bind"],
  },
  {
    id: "split-pdf",
    name: "Split PDF",
    desc: "Extract specific page ranges or separate every single page into individual documents in a ZIP.",
    href: "/split",
    category: "organize",
    categoryLabel: "Organize",
    icon: Scissors,
    colorClass: "bg-purple-600 text-white shadow-purple-500/20",
    badge: "Fast Extraction",
    keywords: ["split", "separate", "divide", "extract", "pages", "ranges", "cut"],
  },
  {
    id: "compress-pdf",
    name: "Compress PDF",
    desc: "Optimize and reduce PDF file size with balanced, recommended, or maximum compression tiers.",
    href: "/compress",
    category: "optimize",
    categoryLabel: "Optimize",
    icon: Minimize2,
    colorClass: "bg-emerald-600 text-white shadow-emerald-500/20",
    badge: "Smart Downsampling",
    keywords: ["compress", "shrink", "reduce", "size", "optimize", "downsample", "smaller", "deflate"],
  },
  {
    id: "rotate-pdf",
    name: "Rotate PDF",
    desc: "Rotate pages 90°, 180°, or 270° clockwise with lossless page-dictionary rotation.",
    href: "/rotate",
    category: "organize",
    categoryLabel: "Organize",
    icon: RotateCw,
    colorClass: "bg-indigo-600 text-white shadow-indigo-500/20",
    badge: "Lossless",
    keywords: ["rotate", "turn", "orientation", "clockwise", "angle", "landscape", "portrait"],
  },
  {
    id: "watermark-pdf",
    name: "Watermark PDF",
    desc: "Stamp customizable text watermarks with precision opacity, rotation, color, and positions.",
    href: "/watermark",
    category: "security",
    categoryLabel: "Security",
    icon: Stamp,
    colorClass: "bg-amber-600 text-white shadow-amber-500/20",
    badge: "Custom Text",
    keywords: ["watermark", "stamp", "draft", "confidential", "brand", "text", "overlay"],
  },
  {
    id: "page-numbers",
    name: "Page Numbers",
    desc: "Add customizable header or footer page numbers with versatile positions, styles, and numbering offsets.",
    href: "/page-numbers",
    category: "organize",
    categoryLabel: "Organize",
    icon: Hash,
    colorClass: "bg-teal-600 text-white shadow-teal-500/20",
    badge: "Headers & Footers",
    keywords: ["page numbers", "numbering", "header", "footer", "paginate", "counter", "pagination"],
  },
  {
    id: "protect-pdf",
    name: "Protect PDF",
    desc: "Encrypt your PDF with standard AES-256 password protection to prevent unauthorized access.",
    href: "/protect",
    category: "security",
    categoryLabel: "Security",
    icon: Lock,
    colorClass: "bg-rose-600 text-white shadow-rose-500/20",
    badge: "AES-256",
    keywords: ["protect", "encrypt", "password", "lock", "security", "aes-256", "private"],
  },
  {
    id: "unlock-pdf",
    name: "Unlock PDF",
    desc: "Remove password security and encryption from protected PDFs using your document password.",
    href: "/unlock",
    category: "security",
    categoryLabel: "Security",
    icon: Unlock,
    colorClass: "bg-cyan-600 text-white shadow-cyan-500/20",
    badge: "Decryption",
    keywords: ["unlock", "decrypt", "remove password", "open", "unprotect", "security"],
  },
  {
    id: "extract-pages",
    name: "Extract Pages",
    desc: "Extract custom individual pages or complex ranges into a clean standalone PDF document.",
    href: "/extract-pages",
    category: "organize",
    categoryLabel: "Organize",
    icon: FileSpreadsheet,
    colorClass: "bg-violet-600 text-white shadow-violet-500/20",
    badge: "Selective Export",
    keywords: ["extract pages", "pull pages", "select pages", "filter", "ranges", "isolate"],
  },
  {
    id: "organize-pdf",
    name: "Organize PDF",
    desc: "Reorder, rotate, delete, or duplicate pages with interactive visual thumbnail drag-and-drop.",
    href: "/organize-pdf",
    category: "organize",
    categoryLabel: "Organize",
    icon: LayoutGrid,
    colorClass: "bg-sky-600 text-white shadow-sky-500/20",
    badge: "Visual Thumbnails",
    keywords: ["organize", "reorder", "sort", "delete pages", "duplicate", "grid", "visual", "drag and drop"],
  },
  {
    id: "pdf-to-jpg",
    name: "PDF to JPG",
    desc: "Convert every page into high-definition JPEG images at 150 or 300 DPI packaged in a ZIP archive.",
    href: "/pdf-to-jpg",
    category: "convert",
    categoryLabel: "Convert",
    icon: ImageIcon,
    colorClass: "bg-orange-600 text-white shadow-orange-500/20",
    badge: "150 & 300 DPI",
    keywords: ["pdf to jpg", "convert", "jpeg", "image", "export", "extract images", "dpi", "picture"],
  },
  {
    id: "jpg-to-pdf",
    name: "JPG to PDF",
    desc: "Convert and sequence multiple JPG/JPEG images into a single organized PDF with page sizing options.",
    href: "/jpg-to-pdf",
    category: "convert",
    categoryLabel: "Convert",
    icon: ImageIcon,
    colorClass: "bg-red-600 text-white shadow-red-500/20",
    badge: "Multi-Image",
    keywords: ["jpg to pdf", "image to pdf", "convert", "jpeg", "photos", "album", "a4", "pictures"],
  },
  {
    id: "repair-pdf",
    name: "Repair PDF",
    desc: "Reconstruct damaged cross-reference tables, fix stream errors, and salvage corrupted PDF documents.",
    href: "/repair-pdf",
    category: "optimize",
    categoryLabel: "Optimize",
    icon: Wrench,
    colorClass: "bg-amber-700 text-white shadow-amber-600/20",
    badge: "Structural Salvage",
    keywords: ["repair", "fix", "recover", "salvage", "corrupted", "damaged", "xref", "restore", "broken"],
  },
];

const CATEGORIES: { id: ToolCategory; label: string }[] = [
  { id: "all", label: "All Tools" },
  { id: "organize", label: "Organize" },
  { id: "optimize", label: "Optimize" },
  { id: "convert", label: "Convert" },
  { id: "security", label: "Security" },
];

export default function AllToolsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<ToolCategory>("all");
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Focus search bar on pressing "/"
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "/" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Filter tools based on search query and category
  const filteredTools = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return TOOLS.filter((tool) => {
      // Category filter
      if (activeCategory !== "all" && tool.category !== activeCategory) {
        return false;
      }

      // Query filter
      if (!query) return true;

      const inName = tool.name.toLowerCase().includes(query);
      const inDesc = tool.desc.toLowerCase().includes(query);
      const inCategory = tool.categoryLabel.toLowerCase().includes(query);
      const inKeywords = tool.keywords.some((k) => k.toLowerCase().includes(query));

      return inName || inDesc || inCategory || inKeywords;
    });
  }, [searchQuery, activeCategory]);

  const handleResetFilters = () => {
    setSearchQuery("");
    setActiveCategory("all");
    searchInputRef.current?.focus();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <Navbar currentToolName="All Tools" />

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
        {/* Page Hero Header */}
        <div className="text-center space-y-3 max-w-3xl mx-auto pt-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/60">
            <Sparkles className="w-3.5 h-3.5" />
            12 Browser-Grade PDF & Image Tools
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            All PDF Tools
          </h1>
          <p className="text-base sm:text-lg text-gray-600 dark:text-gray-300 leading-relaxed max-w-2xl mx-auto">
            Process, organize, convert, and protect your documents privately with zero third-party cloud conversion dependencies.
          </p>
        </div>

        {/* Search & Filter Controls */}
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              id="tool-search-input"
              data-testid="tool-search-input"
              placeholder="Search PDF tools (e.g., merge, compress, protect, jpg)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-11 pr-20 py-3 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:text-base text-gray-900 dark:text-white placeholder:text-gray-400 transition-all"
            />
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear search"
                  className="p-1 rounded-md text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <kbd className="hidden sm:inline-block px-2 py-0.5 text-[11px] font-mono text-gray-400 bg-gray-100 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                /
              </kbd>
            </div>
          </div>

          {/* Category Filter Pills & Result Counter */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Tool Categories">
              {CATEGORIES.map((cat) => {
                const isActive = activeCategory === cat.id;
                const count =
                  cat.id === "all"
                    ? TOOLS.length
                    : TOOLS.filter((t) => t.category === cat.id).length;

                return (
                  <button
                    key={cat.id}
                    role="tab"
                    id={`category-tab-${cat.id}`}
                    aria-selected={isActive}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all flex items-center gap-1.5 ${
                      isActive
                        ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                        : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span>{cat.label}</span>
                    <span
                      className={`text-[11px] px-1.5 py-0.2 rounded-full font-semibold ${
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

            <div className="text-xs text-gray-500 dark:text-gray-400 font-medium ml-auto">
              Showing {filteredTools.length} of {TOOLS.length} tools
            </div>
          </div>
        </div>

        {/* Tools Grid */}
        {filteredTools.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 pt-2">
            {filteredTools.map((tool) => {
              const Icon = tool.icon;
              return (
                <Link
                  key={tool.id}
                  href={tool.href}
                  id={`tool-card-${tool.id}`}
                  data-testid={`tool-card-${tool.id}`}
                  className="group block h-full focus:outline-none"
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
                        {tool.name}
                        <ArrowRight className="w-4 h-4 text-blue-500 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all duration-200" />
                      </CardTitle>
                      <CardDescription className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed pt-1">
                        {tool.desc}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0 pb-4">
                      <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800/80 text-xs">
                        <span className="text-[11px] font-medium text-blue-600 dark:text-blue-400">
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
        ) : (
          /* Empty State */
          <div
            id="empty-tools-state"
            data-testid="empty-tools-state"
            className="py-16 text-center max-w-md mx-auto space-y-4"
          >
            <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 flex items-center justify-center mx-auto shadow-inner">
              <Search className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                No tools found
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {searchQuery
                  ? `No PDF tools match "${searchQuery}" in the selected category.`
                  : "No PDF tools match the selected category."}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={handleResetFilters}
              className="mt-2 text-sm font-semibold"
            >
              Reset Search & Filters
            </Button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-8 mt-16 text-center text-xs text-gray-500 dark:text-gray-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-2">
          <p className="font-semibold text-gray-700 dark:text-gray-300">
            DocForge — Private, Open-Source PDF Platform
          </p>
          <p>All processing runs within your own local Docker infrastructure. No external APIs.</p>
        </div>
      </footer>
    </div>
  );
}
