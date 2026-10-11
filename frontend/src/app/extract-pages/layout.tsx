import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("extract-pages");

export default function ExtractPagesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
