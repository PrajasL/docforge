import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("page-numbers");

export default function PageNumbersLayout({ children }: { children: React.ReactNode }) {
  return children;
}
