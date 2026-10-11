import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("unlock");

export default function UnlockLayout({ children }: { children: React.ReactNode }) {
  return children;
}
