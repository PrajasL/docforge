import React from "react";
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
  Wrench,
} from "lucide-react";

export type ToolCategory = "all" | "organize" | "optimize" | "convert" | "security";

export interface ToolItem {
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

export const CATEGORIES: { id: ToolCategory; label: string }[] = [
  { id: "all", label: "All Tools" },
  { id: "organize", label: "Organize" },
  { id: "optimize", label: "Optimize" },
  { id: "convert", label: "Convert" },
  { id: "security", label: "Security" },
];

export const POPULAR_TOOL_IDS = [
  "merge-pdf",
  "split-pdf",
  "compress-pdf",
  "organize-pdf",
  "pdf-to-jpg",
];

export const POPULAR_TOOLS = TOOLS.filter((tool) =>
  POPULAR_TOOL_IDS.includes(tool.id)
);
