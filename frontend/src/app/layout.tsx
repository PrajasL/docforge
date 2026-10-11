import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/context/theme-context";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { getSiteUrl } from "@/config/tools-seo";

export const metadata: Metadata = {
  metadataBase: new URL(getSiteUrl()),
  title: "DocForge - Free, Private & Powerful PDF Tools",
  description:
    "Merge, split, compress, organize, convert, and secure your PDF documents privately without third-party APIs. 100% private and free.",
  alternates: {
    canonical: `${getSiteUrl()}/`,
  },
  openGraph: {
    title: "DocForge - Free, Private & Powerful PDF Tools",
    description:
      "Merge, split, compress, organize, convert, and secure your PDF documents privately without third-party APIs. 100% private and free.",
    url: `${getSiteUrl()}/`,
    siteName: "DocForge",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DocForge - Free, Private & Powerful PDF Tools",
    description:
      "Merge, split, compress, organize, convert, and secure your PDF documents privately without third-party APIs. 100% private and free.",
  },
};

const themeScript = `(function() {
  try {
    var stored = localStorage.getItem('docforge_theme');
    var isDark = stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch (e) {}
})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100 transition-colors duration-150">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}

