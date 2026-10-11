"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Zap,
  Lock,
  Clock,
  ArrowRight,
  HelpCircle,
  ListOrdered,
  Layers,
} from "lucide-react";
import { ToolSeoData, generateToolJsonLd, getSiteUrl } from "@/config/tools-seo";

interface ToolSeoSectionProps {
  tool: ToolSeoData;
}

export function ToolSeoSection({ tool }: ToolSeoSectionProps) {
  const siteUrl = getSiteUrl();
  const jsonLd = generateToolJsonLd(tool, siteUrl);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 mt-16 space-y-16 pb-12">
      {/* Inject Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Step-by-Step How-To Section */}
      <section
        aria-labelledby="how-to-heading"
        className="rounded-2xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900/60 p-6 sm:p-8 shadow-sm"
      >
        <div className="flex items-center gap-2.5 text-blue-600 dark:text-blue-400 font-semibold text-xs tracking-wider uppercase mb-2">
          <ListOrdered className="w-4 h-4" />
          <span>Step-by-Step Guide</span>
        </div>
        <h2
          id="how-to-heading"
          className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3"
        >
          {tool.howToName}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-8 max-w-2xl">
          {tool.howToDescription}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {tool.steps.map((step, idx) => (
            <div
              key={idx}
              className="relative rounded-xl border border-gray-100 dark:border-gray-800/80 bg-gray-50/70 dark:bg-gray-900 p-5 flex flex-col justify-between"
            >
              <div>
                <div className="w-8 h-8 rounded-lg bg-blue-600 text-white font-bold text-sm flex items-center justify-center mb-3 shadow-sm shadow-blue-500/20">
                  {idx + 1}
                </div>
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1.5">
                  {step.name}
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                  {step.text}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Key Guarantees & Features */}
      <section
        aria-labelledby="features-heading"
        className="rounded-2xl border border-gray-200/80 dark:border-gray-800 bg-gradient-to-b from-gray-50/50 to-white dark:from-gray-900/40 dark:to-gray-900/80 p-6 sm:p-8 shadow-sm"
      >
        <div className="text-center max-w-xl mx-auto mb-8">
          <h2
            id="features-heading"
            className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2"
          >
            Why Process PDFs with DocForge?
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Engineered for security, private workflows, and dependable document processing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex flex-col items-center text-center p-4">
            <div className="w-12 h-12 rounded-xl bg-green-50 dark:bg-green-950/40 text-green-600 dark:text-green-400 flex items-center justify-center mb-3">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1">
              Dedicated Private Processing
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              Files are uploaded securely and processed directly on DocForge&apos;s isolated worker servers. We never transmit your document data to third-party conversion APIs or cloud AI models.
            </p>

          </div>

          <div className="flex flex-col items-center text-center p-4">
            <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-3">
              <Clock className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1">
              Automatic 2-Hour File Deletion
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              Your uploaded and converted files are scheduled for automatic permanent deletion after 2 hours. Your privacy is guaranteed.
            </p>
          </div>

          <div className="flex flex-col items-center text-center p-4">
            <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-3">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1">
              Fast & Free, No Registration
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              No account creation, email confirmation, or hidden paywalls required. Immediate access to all tool features whenever you need them.
            </p>
          </div>
        </div>
      </section>

      {/* Frequently Asked Questions */}
      <section
        aria-labelledby="faq-heading"
        className="rounded-2xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900/60 p-6 sm:p-8 shadow-sm"
      >
        <div className="flex items-center gap-2.5 text-blue-600 dark:text-blue-400 font-semibold text-xs tracking-wider uppercase mb-2">
          <HelpCircle className="w-4 h-4" />
          <span>Knowledge Base</span>
        </div>
        <h2
          id="faq-heading"
          className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-6"
        >
          Frequently Asked Questions
        </h2>

        <div className="divide-y divide-gray-100 dark:divide-gray-800/80">
          {tool.faqs.map((faq, idx) => (
            <article key={idx} className="py-4 first:pt-0 last:pb-0">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1.5 flex items-start gap-2">
                <span className="text-blue-700 dark:text-blue-400 font-bold">Q.</span>
                <span>{faq.question}</span>
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed pl-5">
                {faq.answer}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Related Tools Linking Mesh */}
      <section
        aria-labelledby="related-tools-heading"
        className="rounded-2xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900/60 p-6 sm:p-8 shadow-sm"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2.5 text-blue-600 dark:text-blue-400 font-semibold text-xs tracking-wider uppercase mb-1">
              <Layers className="w-4 h-4" />
              <span>Explore More Tools</span>
            </div>
            <h2
              id="related-tools-heading"
              className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white"
            >
              Related PDF Utilities
            </h2>
          </div>
          <Link
            href="/tools"
            className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
          >
            <span>All 12 Tools</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {tool.relatedTools.map((rel, idx) => (
            <Link
              key={idx}
              href={rel.href}
              className="group rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/80 p-4 hover:border-blue-400 dark:hover:border-blue-500 transition-all hover:shadow-sm flex flex-col justify-between"
            >
              <div>
                <span className="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 mb-2">
                  {rel.category}
                </span>
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center justify-between">
                  <span>{rel.name}</span>
                  <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                  {rel.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
