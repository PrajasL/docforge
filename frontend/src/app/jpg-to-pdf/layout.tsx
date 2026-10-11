import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("jpg-to-pdf");

export default function JpgToPdfLayout({ children }: { children: React.ReactNode }) {
  return children;
}
