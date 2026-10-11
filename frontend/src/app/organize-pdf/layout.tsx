import type { Metadata } from "next";
import { getToolMetadata } from "@/config/tools-seo";

export const metadata: Metadata = getToolMetadata("organize-pdf");

export default function OrganizePdfLayout({ children }: { children: React.ReactNode }) {
  return children;
}
