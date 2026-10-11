import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("repair-pdf");

export default function RepairPdfLayout({ children }: { children: React.ReactNode }) {
  return children;
}
