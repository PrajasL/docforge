import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("protect");

export default function ProtectLayout({ children }: { children: React.ReactNode }) {
  return children;
}
