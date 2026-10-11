import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("merge");

export default function MergeLayout({ children }: { children: React.ReactNode }) {
  return children;
}
