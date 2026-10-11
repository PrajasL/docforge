import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("compress");

export default function CompressLayout({ children }: { children: React.ReactNode }) {
  return children;
}
