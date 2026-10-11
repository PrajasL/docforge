"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  FileText,
  Layers,
  Scissors,
  Minimize2,
  RotateCw,
  Stamp,
  Hash,
  Lock,
  Unlock,
  FileSpreadsheet,
  LayoutGrid,
  Server,
  Database,
  HardDrive,
  Cpu,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ExternalLink,
  Image as ImageIcon,
  Wrench,
} from "lucide-react";

interface ServiceHealth {
  status: string;
  error?: string;
  buckets_available?: string[];
}

interface ReadinessData {
  status: string;
  service: string;
  version: string;
  services: {
    database: ServiceHealth;
    redis: ServiceHealth;
    storage: ServiceHealth;
  };
}

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [healthData, setHealthData] = useState<ReadinessData | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/health/ready`);
      const json = await res.json();
      if (json.data) {
        setHealthData(json.data);
      } else {
        setFetchError("Received unexpected response format from backend.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend";
      setFetchError(msg);
    } finally {
      setLoading(false);
    }
  };

  const upcomingTools = [
    {
      name: "Merge PDF",
      desc: "Combine multiple PDF files into a single unified document.",
      icon: Layers,
      phase: "Phase 1 / Available Now",
      href: "/merge",
    },
    {
      name: "Split PDF",
      desc: "Extract specific page ranges or split each page into files.",
      icon: Scissors,
      phase: "Phase 2 / Available Now",
      href: "/split",
    },
    {
      name: "Compress PDF",
      desc: "Optimize and reduce PDF file size while retaining quality.",
      icon: Minimize2,
      phase: "Phase 2 / Available Now",
      href: "/compress",
    },
    {
      name: "Rotate PDF",
      desc: "Rotate individual or all pages clockwise or counter-clockwise.",
      icon: RotateCw,
      phase: "Phase 2 / Available Now",
      href: "/rotate",
    },
    {
      name: "Watermark PDF",
      desc: "Apply customizable text watermarks to your PDF documents.",
      icon: Stamp,
      phase: "Phase 2 / Available Now",
      href: "/watermark",
    },
    {
      name: "Page Numbers",
      desc: "Stamp customizable page numbers with multiple positions and formats.",
      icon: Hash,
      phase: "Phase 2 / Available Now",
      href: "/page-numbers",
    },
    {
      name: "Protect PDF",
      desc: "Encrypt your PDF with strong AES-256 password protection.",
      icon: Lock,
      phase: "Phase 2 / Available Now",
      href: "/protect",
    },
    {
      name: "Unlock PDF",
      desc: "Remove password security from your PDF if you know the password.",
      icon: Unlock,
      phase: "Phase 2 / Available Now",
      href: "/unlock",
    },
    {
      name: "Extract Pages",
      desc: "Extract specific pages or page ranges into a single organized PDF document.",
      icon: FileSpreadsheet,
      phase: "Phase 2 / Available Now",
      href: "/extract-pages",
    },
    {
      name: "Organize PDF",
      desc: "Reorder, rotate, delete, or duplicate pages with visual drag-and-drop.",
      icon: LayoutGrid,
      phase: "Phase 3 / Available Now",
      href: "/organize-pdf",
    },
    {
      name: "PDF to JPG",
      desc: "Convert every PDF page into individual high-quality JPG images packaged in a ZIP.",
      icon: ImageIcon,
      phase: "Phase 3 / Available Now",
      href: "/pdf-to-jpg",
    },
    {
      name: "JPG to PDF",
      desc: "Convert and combine multiple JPG/JPEG images into a single organized PDF document.",
      icon: ImageIcon,
      phase: "Phase 3 / Available Now",
      href: "/jpg-to-pdf",
    },
    {
      name: "Repair PDF",
      desc: "Reconstruct damaged cross-reference tables and salvage corrupted PDF documents.",
      icon: Wrench,
      phase: "Phase 4 / Available Now",
      href: "/repair-pdf",
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
                DocForge
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                Phase 1: Foundation
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-2 sm:space-x-4">
            <Link
              href="/tools"
              className="inline-flex items-center text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              <LayoutGrid className="w-4 h-4 mr-1.5 text-blue-500" />
              All Tools
            </Link>
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-blue-600 transition-colors"
            >
              API Docs
              <ExternalLink className="w-3.5 h-3.5 ml-1" />
            </a>
            <Button size="sm" onClick={checkHealth} disabled={loading} variant="outline" className="hidden sm:inline-flex">
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Probe Backend
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-12">
        {/* Hero Section */}
        <div className="text-center space-y-4 max-w-3xl mx-auto pt-6">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            High-Performance, Secure <br />
            <span className="text-blue-600">PDF Processing Platform</span>
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 leading-relaxed">
            Welcome to the local development environment for DocForge. Phase 1 establishes
            the core foundation: Next.js frontend, FastAPI backend, PostgreSQL, Redis, and MinIO S3 storage.
          </p>
        </div>

        {/* Infrastructure & Backend Health Panel */}
        <section aria-labelledby="infra-heading" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 id="infra-heading" className="text-xl font-semibold tracking-tight">
              Platform Environment & Services
            </h2>
            <span className="text-xs text-gray-600 dark:text-gray-400">Live Status Probe</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* FastAPI Service */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Server className="w-5 h-5 text-blue-600" />
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                    Port 8000
                  </span>
                </div>
                <CardTitle className="text-base mt-2">FastAPI Backend</CardTitle>
                <CardDescription>REST API & Task Dispatcher</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-gray-600 dark:text-gray-300">
                Endpoints: <code className="text-blue-600 dark:text-blue-400 font-mono">/health</code>, <code className="text-blue-600 dark:text-blue-400 font-mono">/api/v1</code>
              </CardContent>
            </Card>

            {/* PostgreSQL Service */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Database className="w-5 h-5 text-indigo-600" />
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    Port 5432
                  </span>
                </div>
                <CardTitle className="text-base mt-2">PostgreSQL 16</CardTitle>
                <CardDescription>ACID Relational Storage</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-gray-600 dark:text-gray-300">
                Status: {healthData?.services?.database?.status === "connected" ? (
                  <span className="text-green-600 font-medium inline-flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <span className="text-gray-500 dark:text-gray-400">Ready via Docker Compose</span>
                )}
              </CardContent>
            </Card>

            {/* Redis Service */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Cpu className="w-5 h-5 text-red-500" />
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    Port 6379
                  </span>
                </div>
                <CardTitle className="text-base mt-2">Redis 7</CardTitle>
                <CardDescription>Broker & State Cache</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-gray-600 dark:text-gray-300">
                Status: {healthData?.services?.redis?.status === "connected" ? (
                  <span className="text-green-600 font-medium inline-flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <span className="text-gray-500 dark:text-gray-400">Ready via Docker Compose</span>
                )}
              </CardContent>
            </Card>

            {/* MinIO Object Storage */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <HardDrive className="w-5 h-5 text-amber-500" />
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    Port 9000
                  </span>
                </div>
                <CardTitle className="text-base mt-2">MinIO Storage</CardTitle>
                <CardDescription>S3-Compatible Object Store</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-gray-600 dark:text-gray-300">
                Status: {healthData?.services?.storage?.status === "connected" ? (
                  <span className="text-green-600 font-medium inline-flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <span className="text-gray-500 dark:text-gray-400">Ready via Docker Compose</span>
                )}
              </CardContent>
            </Card>
          </div>

          {fetchError && (
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-300 text-sm flex items-center space-x-2">
              <XCircle className="w-4 h-4 flex-shrink-0" />
              <span>Could not reach backend at http://localhost:8000: {fetchError}</span>
            </div>
          )}

          {healthData && (
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 text-blue-900 dark:text-blue-300 text-sm">
              <div className="font-semibold mb-1">
                Backend Status Response ({healthData.service} v{healthData.version}): {healthData.status}
              </div>
              <pre className="text-xs overflow-x-auto p-2 bg-white/50 dark:bg-black/40 rounded mt-2">
                {JSON.stringify(healthData.services, null, 2)}
              </pre>
            </div>
          )}
        </section>

        {/* Tools Grid */}
        <section aria-labelledby="tools-heading" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 id="tools-heading" className="text-xl font-semibold tracking-tight text-gray-900 dark:text-white">
                Available PDF Tools (12 Tools Operational)
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Processed privately on DocForge&apos;s isolated worker pipeline with zero third-party APIs.
              </p>
            </div>
            <Link
              href="/tools"
              className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              View All Tools Directory &rarr;
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {upcomingTools.map((tool) => {
              const Icon = tool.icon;
              const content = (
                <Card className={`h-full hover:border-blue-400/50 transition-all ${tool.href ? "hover:shadow-md cursor-pointer group" : ""}`}>
                  <CardHeader>
                    <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center mb-2 group-hover:scale-105 transition-transform">
                      <Icon className="w-5 h-5" />
                    </div>
                    <CardTitle className="text-base flex items-center justify-between">
                      {tool.name}
                      {tool.href && <ExternalLink className="w-4 h-4 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />}
                    </CardTitle>
                    <CardDescription className="text-xs">{tool.desc}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${tool.href ? "text-blue-700 bg-blue-50 dark:text-blue-300 dark:bg-blue-900/30" : "text-gray-500 bg-gray-100 dark:bg-gray-800"}`}>
                      {tool.phase}
                    </span>
                  </CardContent>
                </Card>
              );

              return tool.href ? (
                <Link key={tool.name} href={tool.href} className="block">
                  {content}
                </Link>
              ) : (
                <div key={tool.name}>{content}</div>
              );
            })}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-8 text-xs text-gray-600 dark:text-gray-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-center sm:text-left">
            DocForge &copy; 2026 &mdash; Modular Monolith PDF Processing Engine. 100% Private, Self-Hosted Utilities.
          </p>
          <nav aria-label="Legal and Navigation Links" className="flex items-center gap-6">
            <Link
              href="/privacy"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1"
            >
              Privacy Policy
            </Link>
            <Link
              href="/terms"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1"
            >
              Terms of Service
            </Link>
            <Link
              href="/tools"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1"
            >
              All Tools
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
