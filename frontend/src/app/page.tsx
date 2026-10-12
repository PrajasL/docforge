import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { HomepageToolsGrid } from "@/components/homepage-tools-grid";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  ShieldCheck,
  Clock,
  Zap,
  FileCheck2,
  ArrowRight,
  Upload,
  Cpu,
  Download,
  CheckCircle2,
  HelpCircle,
  Layers,
  LayoutGrid,
} from "lucide-react";
import {
  getSiteUrl,
  HOMEPAGE_FAQS,
  generateHomepageJsonLd,
} from "@/config/tools-seo";
import { POPULAR_TOOLS } from "@/config/tools-list";

export const metadata: Metadata = {
  title: "DocForge — Free, Private & Secure Online PDF Tools",
  description:
    "Free online PDF tools: merge, split, compress, rotate, watermark, page numbers, protect, unlock, extract pages, organize, convert, and repair PDF documents privately without external cloud APIs.",
  alternates: {
    canonical: `${getSiteUrl()}/`,
  },
  openGraph: {
    title: "DocForge — Free, Private & Secure Online PDF Tools",
    description:
      "Free online PDF tools: merge, split, compress, rotate, watermark, page numbers, protect, unlock, extract pages, organize, convert, and repair PDF documents privately without external cloud APIs.",
    url: `${getSiteUrl()}/`,
    siteName: "DocForge",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DocForge — Free, Private & Secure Online PDF Tools",
    description:
      "Free online PDF tools: merge, split, compress, rotate, watermark, page numbers, protect, unlock, extract pages, organize, convert, and repair PDF documents privately without external cloud APIs.",
  },
};

export default function Home() {
  const siteUrl = getSiteUrl();
  const homepageJsonLd = generateHomepageJsonLd(siteUrl);

  const trustHighlights = [
    {
      icon: ShieldCheck,
      title: "100% Private Sandbox",
      desc: "Processed in isolated local containers with zero third-party APIs or external document leaks.",
    },
    {
      icon: Clock,
      title: "60-Min Auto Cleanup",
      desc: "Uploaded and processed files are permanently purged from server storage within 60 minutes.",
    },
    {
      icon: Zap,
      title: "Browser-Grade & Free",
      desc: "Instant processing with zero fees, no subscription walls, and no mandatory account creation.",
    },
    {
      icon: FileCheck2,
      title: "Lossless Formatting",
      desc: "High-fidelity PDF processing preserving vector geometry, text clarity, and embedded fonts.",
    },
  ];

  const howItWorksSteps = [
    {
      step: "01",
      icon: Upload,
      title: "Select & Configure",
      description:
        "Upload your PDF or images through the drag-and-drop interface. Customize page ranges, rotation angles, watermarks, or compression presets with instant feedback.",
    },
    {
      step: "02",
      icon: Cpu,
      title: "Isolated Processing",
      description:
        "Your task executes in a dedicated backend worker sandbox powered by industry-standard libraries (pikepdf, pypdf, pdf2image) with strict resource quotas.",
    },
    {
      step: "03",
      icon: Download,
      title: "Instant Download & Purge",
      description:
        "Download your finished document immediately. All temporary files are automatically and permanently deleted from storage within 60 minutes.",
    },
  ];

  const securityFeatures = [
    {
      title: "Automated Lifecycle Purge",
      desc: "Background cleanup workers run on a recurring schedule to permanently delete upload and result artifacts within 60 minutes.",
    },
    {
      title: "Zero Third-Party Cloud Leaks",
      desc: "All conversions and operations run self-hosted inside DocForge's own infrastructure. No files are ever sent to commercial external cloud APIs.",
    },
    {
      title: "No AI Model Training",
      desc: "Your documents are strictly confidential. We never read, index, or use your uploaded text or images to train AI or machine learning models.",
    },
    {
      title: "Antivirus & MIME Inspection",
      desc: "Uploads pass thorough validation including MIME type verification, magic-byte inspection, and ClamAV scanning before any processing begins.",
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Structured Data (JSON-LD) */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(homepageJsonLd) }}
      />

      {/* Top Navigation */}
      <Navbar />

      {/* Main Content */}
      <main className="flex-1 w-full space-y-20 pb-20">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-12 pb-16 sm:pt-20 sm:pb-24 border-b border-gray-200/80 dark:border-gray-800/80 bg-gradient-to-b from-white via-blue-50/20 to-gray-50 dark:from-gray-900 dark:via-gray-900/50 dark:to-gray-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs sm:text-sm font-semibold bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60 shadow-sm">
              <ShieldCheck className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>13 Production PDF Utilities &bull; 100% Private Processing</span>
            </div>

            <div className="max-w-4xl mx-auto space-y-4">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 dark:text-white leading-[1.12]">
                Free, Private & Secure <br />
                <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  Online PDF Tools
                </span>
              </h1>
              <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-300 leading-relaxed max-w-3xl mx-auto">
                Merge, split, compress, rotate, organize, convert, and protect PDF documents right in your browser.
                Processed securely on our isolated worker pipeline with automatic file deletion within 60 minutes — zero third-party APIs, zero tracking, zero AI training on your documents.
              </p>
            </div>

            {/* Hero Calls to Action */}
            <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
              <Link href="#tools">
                <Button size="lg" className="px-6 py-6 text-base font-semibold shadow-lg shadow-blue-500/20 gap-2">
                  Explore All 13 Tools
                  <ArrowRight className="w-5 h-5" />
                </Button>
              </Link>
              <Link href="/merge">
                <Button size="lg" variant="outline" className="px-6 py-6 text-base font-semibold gap-2">
                  <Layers className="w-5 h-5 text-blue-600" />
                  Most Popular: Merge PDF
                </Button>
              </Link>
            </div>

            {/* Popular Tools Quick Strip */}
            <div className="pt-6 max-w-4xl mx-auto">
              <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
                Quick Shortcuts to Most Popular Utilities:
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2.5">
                {POPULAR_TOOLS.map((tool) => (
                  <Link
                    key={tool.id}
                    href={tool.href}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-medium bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 shadow-sm hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-all"
                  >
                    <span>{tool.name}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
                  </Link>
                ))}
              </div>
            </div>

            {/* Trust Highlights Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-10 text-left max-w-6xl mx-auto">
              {trustHighlights.map((item) => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.title}
                    className="p-5 rounded-2xl bg-white/80 dark:bg-gray-900/80 border border-gray-200/80 dark:border-gray-800/80 backdrop-blur shadow-sm space-y-2"
                  >
                    <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="font-bold text-sm text-gray-900 dark:text-white">
                      {item.title}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                      {item.desc}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* PDF Tools Discovery Section */}
        <section id="tools" aria-labelledby="tools-heading" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8 scroll-mt-20">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                <span>Production PDF Utilities</span>
              </div>
              <h2 id="tools-heading" className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
                All 13 Online PDF Tools
              </h2>
              <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300 max-w-2xl">
                Every tool is engineered for speed, privacy, and precision formatting. Process documents locally without cloud exposure.
              </p>
            </div>
            <Link
              href="/tools"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 dark:text-blue-400 hover:underline shrink-0"
            >
              <LayoutGrid className="w-4 h-4" />
              Open Searchable Directory &rarr;
            </Link>
          </div>

          {/* Interactive Tools Grid Component with Tabs */}
          <HomepageToolsGrid />
        </section>

        {/* How It Works Section */}
        <section
          id="how-it-works"
          aria-labelledby="how-it-works-heading"
          className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10 scroll-mt-20 pt-8"
        >
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              <span>Simple Workflow</span>
            </div>
            <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              How DocForge Works
            </h2>
            <p className="text-base text-gray-600 dark:text-gray-300">
              Three straightforward steps to process any PDF with guaranteed data privacy and zero hassle.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorksSteps.map((step) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.step}
                  className="relative p-6 rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col justify-between space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-3xl font-black text-gray-200 dark:text-gray-800 font-mono">
                      {step.step}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                      {step.title}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Security & Privacy Section */}
        <section
          id="security"
          aria-labelledby="security-heading"
          className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 scroll-mt-20 pt-8"
        >
          <div className="rounded-3xl bg-gradient-to-br from-blue-900 to-indigo-950 text-white p-8 sm:p-12 lg:p-16 shadow-xl space-y-10">
            <div className="max-w-3xl space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-800/80 text-blue-200 border border-blue-700">
                <ShieldCheck className="w-4 h-4" />
                <span>Security & Privacy by Design</span>
              </div>
              <h2 id="security-heading" className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
                Engineered for Complete Document Privacy
              </h2>
              <p className="text-base sm:text-lg text-blue-100/90 leading-relaxed">
                Most online PDF services upload your files to third-party cloud infrastructure or store data indefinitely.
                DocForge runs on isolated worker containers and permanently purges all files within 60 minutes.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {securityFeatures.map((feat) => (
                <div
                  key={feat.title}
                  className="p-6 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/10 space-y-2"
                >
                  <div className="flex items-center gap-2 font-bold text-base text-white">
                    <CheckCircle2 className="w-5 h-5 text-blue-400 shrink-0" />
                    <span>{feat.title}</span>
                  </div>
                  <p className="text-sm text-blue-100/80 leading-relaxed pl-7">
                    {feat.desc}
                  </p>
                </div>
              ))}
            </div>

            <div className="pt-2 flex flex-wrap items-center gap-6 text-sm text-blue-200">
              <Link href="/privacy" className="underline hover:text-white transition-colors">
                Read our Privacy Policy &rarr;
              </Link>
              <Link href="/terms" className="underline hover:text-white transition-colors">
                Terms of Service &rarr;
              </Link>
            </div>
          </div>
        </section>

        {/* Frequently Asked Questions Section */}
        <section
          id="faq"
          aria-labelledby="faq-heading"
          className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8 scroll-mt-20 pt-8"
        >
          <div className="text-center space-y-3">
            <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              <HelpCircle className="w-4 h-4" />
              <span>Questions & Answers</span>
            </div>
            <h2 id="faq-heading" className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              Frequently Asked Questions
            </h2>
            <p className="text-base text-gray-600 dark:text-gray-300">
              Clear answers regarding privacy, file limits, and document handling on DocForge.
            </p>
          </div>

          <div className="space-y-4">
            {HOMEPAGE_FAQS.map((faq, index) => (
              <Card key={index} className="border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base sm:text-lg font-bold text-gray-900 dark:text-white flex items-start gap-2.5">
                    <span className="text-blue-600 dark:text-blue-400 font-mono text-sm pt-0.5">
                      Q{index + 1}:
                    </span>
                    <span>{faq.question}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-sm text-gray-600 dark:text-gray-400 leading-relaxed pl-9">
                  {faq.answer}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </main>

      {/* Comprehensive Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-12 text-sm text-gray-600 dark:text-gray-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Brand Column */}
            <div className="space-y-3 md:col-span-1">
              <Link href="/" className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold">
                  D
                </div>
                <span className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
                  DocForge
                </span>
              </Link>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                Free, private, and secure online PDF utilities. Processed locally in isolated worker containers with zero third-party tracking.
              </p>
            </div>

            {/* Popular Tools Column */}
            <div className="space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-gray-900 dark:text-white">
                Popular Tools
              </div>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link href="/merge" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Merge PDF
                  </Link>
                </li>
                <li>
                  <Link href="/split" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Split PDF
                  </Link>
                </li>
                <li>
                  <Link href="/compress" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Compress PDF
                  </Link>
                </li>
                <li>
                  <Link href="/organize-pdf" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Organize PDF
                  </Link>
                </li>
                <li>
                  <Link href="/repair-pdf" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Repair PDF
                  </Link>
                </li>
              </ul>
            </div>

            {/* Security & Convert Column */}
            <div className="space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-gray-900 dark:text-white">
                Security & Convert
              </div>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link href="/protect" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Protect PDF
                  </Link>
                </li>
                <li>
                  <Link href="/unlock" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Unlock PDF
                  </Link>
                </li>
                <li>
                  <Link href="/watermark" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Watermark PDF
                  </Link>
                </li>
                <li>
                  <Link href="/pdf-to-jpg" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    PDF to JPG
                  </Link>
                </li>
                <li>
                  <Link href="/jpg-to-pdf" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    JPG to PDF
                  </Link>
                </li>
              </ul>
            </div>

            {/* Platform & Legal Column */}
            <div className="space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-gray-900 dark:text-white">
                Platform & Legal
              </div>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link href="/tools" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    All 13 Tools Directory
                  </Link>
                </li>
                <li>
                  <Link href="#how-it-works" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    How It Works
                  </Link>
                </li>
                <li>
                  <Link href="#security" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Security Architecture
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-6 border-t border-gray-200 dark:border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
            <p>
              DocForge &copy; 2026 &mdash; Modular Monolith PDF Processing Platform. 100% Private, Self-Hosted Utilities.
            </p>
            <div className="flex items-center gap-4">
              <Link href="/privacy" className="hover:text-gray-900 dark:hover:text-gray-300">
                Privacy
              </Link>
              <span>&bull;</span>
              <Link href="/terms" className="hover:text-gray-900 dark:hover:text-gray-300">
                Terms
              </Link>
              <span>&bull;</span>
              <Link href="/tools" className="hover:text-gray-900 dark:hover:text-gray-300">
                Tools Directory
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
