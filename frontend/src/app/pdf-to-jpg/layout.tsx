import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("pdf-to-jpg");

export default function PdfToJpgLayout({ children }: { children: React.ReactNode }) {
  return children;
}
