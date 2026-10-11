import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("watermark");

export default function WatermarkLayout({ children }: { children: React.ReactNode }) {
  return children;
}
