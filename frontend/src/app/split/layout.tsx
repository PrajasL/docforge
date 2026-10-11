import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("split");

export default function SplitLayout({ children }: { children: React.ReactNode }) {
  return children;
}
