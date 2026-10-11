import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("rotate");

export default function RotateLayout({ children }: { children: React.ReactNode }) {
  return children;
}
