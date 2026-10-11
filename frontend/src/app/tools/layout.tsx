import type { Metadata } from "next";
import { getSiteUrl } from "@/config/tools-seo";

export const metadata: Metadata = {
  title: "All PDF Tools — Free, Private & Secure Online PDF Utilities | DocForge",
  description:
    "Browse DocForge's complete directory of 12 free PDF and image conversion tools. Merge, split, compress, organize, convert, and protect PDF files privately without third-party APIs.",
  keywords: [
    "pdf tools",
    "free pdf editor",
    "pdf utilities",
    "merge pdf",
    "compress pdf",
    "pdf to jpg",
    "jpg to pdf",
  ],
  alternates: {
    canonical: `${getSiteUrl()}/tools`,
  },
  openGraph: {
    title: "All PDF Tools — Free, Private & Secure Online PDF Utilities | DocForge",
    description:
      "Browse DocForge's complete directory of 12 free PDF and image conversion tools. Merge, split, compress, organize, convert, and protect PDF files privately without third-party APIs.",
    url: `${getSiteUrl()}/tools`,
    siteName: "DocForge",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "All PDF Tools — Free, Private & Secure Online PDF Utilities | DocForge",
    description:
      "Browse DocForge's complete directory of 12 free PDF and image conversion tools. Merge, split, compress, organize, convert, and protect PDF files privately without third-party APIs.",
  },
};

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
