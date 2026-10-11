import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { FileText, ShieldAlert, Scale, CheckCircle2, AlertTriangle, ArrowLeft } from "lucide-react";
import { getSiteUrl } from "@/config/tools-seo";

export const metadata: Metadata = {
  title: "Terms of Service — DocForge",
  description:
    "Terms of service, fair usage limits, and processing conditions for DocForge PDF utilities. Truthful terms based on DocForge's actual architecture.",
  alternates: {
    canonical: `${getSiteUrl()}/terms`,
  },
  openGraph: {
    title: "Terms of Service — DocForge",
    description:
      "Terms of service, fair usage limits, and processing conditions for DocForge PDF utilities. Two-hour automated expiration, rate limits, and malware scanning.",
    url: `${getSiteUrl()}/terms`,
    siteName: "DocForge",
    locale: "en_US",
    type: "website",
  },
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Skip to Main Content Accessibility Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 z-50 px-4 py-2 bg-blue-600 text-white rounded-md shadow-lg outline-none ring-2 ring-offset-2 ring-blue-500"
      >
        Skip to main content
      </a>

      <Navbar currentToolName="Terms of Service" badge="Legal" />

      <main id="main-content" tabIndex={-1} className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16 focus:outline-none">
        {/* Breadcrumb / Back button */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
        </div>

        <header className="mb-10 space-y-3 border-b border-gray-200 dark:border-gray-800 pb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/60">
            <Scale className="w-3.5 h-3.5" />
            <span>Operational Terms &amp; Fair Use Policy</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            Terms of Service
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Effective Date: October 11, 2026 &bull; Version 1.0 (Implementation Aligned)
          </p>
        </header>

        <div className="prose prose-blue dark:prose-invert max-w-none space-y-10 text-gray-700 dark:text-gray-300 leading-relaxed">
          {/* Key Terms Overview Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 not-prose">
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Your Documents, Your Rights</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                You retain complete ownership of all uploaded and processed files. DocForge claims zero rights.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold">
                <FileText className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Transient Utility Only</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                Files auto-expire after 2 hours. DocForge is not a storage, backup, or archiving provider.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center justify-center font-bold">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Strict Malware Defense</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                Infected uploads are rejected via ClamAV and purged immediately to protect the platform.
              </p>
            </div>
          </div>

          {/* Section 1 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              1. Acceptance of Terms
            </h2>
            <p>
              By accessing, browsing, or using the DocForge web application and associated services, you agree to be legally bound by these Terms of Service. If you do not agree to all terms stated herein, you must immediately cease using DocForge utilities.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              2. Acceptable Use and User Responsibilities
            </h2>
            <p>
              You agree to use DocForge solely for legitimate, lawful document management tasks. You agree <strong>not</strong> to:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Upload files containing malicious code, viruses, trojans, worms, or ransomware.</li>
              <li>Upload files that infringe upon any patent, trademark, copyright, or intellectual property rights of any third party.</li>
              <li>Attempt to circumvent platform rate limits, abuse automated job creation endpoints, or conduct denial-of-service (DoS) attacks.</li>
              <li>Attempt unauthorized penetration, path traversal, container breakouts, or tampering with backend infrastructure.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              3. Service Boundaries and Enforced Resource Limits
            </h2>
            <p>
              To maintain high system availability and fair resource sharing, DocForge programmatically enforces the following operational boundaries:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Max File Size:</strong> 50 MB per PDF document (25 MB per JPEG image in JPG-to-PDF).</li>
              <li><strong>Max Aggregate Job Size:</strong> 250 MB total cumulative payload across all files in a single job.</li>
              <li><strong>Rate Limits:</strong> 20 job creation requests per 60 seconds, 60 upload requests per 60 seconds, and 120 general requests per 60 seconds per client IP address. Exceeding limits triggers an HTTP 429 response with a mandatory <code>Retry-After</code> cooldown.</li>
              <li><strong>JPG-to-PDF Limits:</strong> Maximum 50 images per job; maximum 10,000 px dimension; maximum 150 MP cumulative pixels.</li>
              <li><strong>PDF-to-JPG Limits:</strong> Maximum 100 pages at 150 DPI; maximum 50 pages at 300 DPI; maximum 250 MB aggregate ZIP output.</li>
            </ul>
          </section>

          {/* Section 4 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              4. Temporary Processing Lifecycle and No Archiving Warranty
            </h2>
            <p>
              DocForge is strictly an on-demand transformation utility:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Mandatory 2-Hour Expiration:</strong> All uploaded source files and converted output files are permanently deleted after <strong>two (2) hours</strong>. You are solely responsible for downloading and verifying your processed files before expiration.
              </li>
              <li>
                <strong>No Long-Term Storage:</strong> DocForge does not offer document archiving, permanent storage, or disaster recovery services. Do not treat DocForge as your primary or backup storage repository.
              </li>
              <li>
                <strong>Unrecoverable Deletion:</strong> Once the 2-hour TTL expires, file data is irreversibly wiped from object storage and databases.
              </li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              5. Intellectual Property and Open Source Architecture
            </h2>
            <p>
              DocForge is built using strictly permissive open-source libraries:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>DocForge Platform:</strong> All software architecture, user interface elements, branding, and workflows are protected by applicable intellectual property laws and permissive open-source licenses (MIT, BSD-3-Clause, Apache 2.0, MPL 2.0) with zero AGPL contamination.
              </li>
              <li>
                <strong>User Content Ownership:</strong> DocForge does not acquire, claim, or license any copyright or ownership over any documents, images, or texts you upload or generate through the platform.
              </li>
            </ul>
          </section>

          {/* Section 6 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              6. Disclaimer of Warranties and Limitation of Liability
            </h2>
            <p>
              THE SERVICE IS PROVIDED ON AN &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; BASIS WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMISSIBLE BY LAW, DOCFORGE DISCLAIMS ALL WARRANTIES, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
            </p>
            <p>
              DocForge does not guarantee that conversions will preserve cryptographic digital signatures (which are inherently invalidated when PDF structures or objects are altered), or that severely corrupted source documents can be recovered without data loss.
            </p>
          </section>

          {/* Section 7 - Operator Action Items */}
          <section className="space-y-4 not-prose p-6 rounded-2xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <h2 className="text-lg">7. Operator Notice: Production Legal Customization Required</h2>
            </div>
            <p className="text-sm text-amber-900/90 dark:text-amber-200/90 leading-relaxed">
              These Terms of Service accurately represent the technical functionality of DocForge. Prior to commercial public launch, the platform owner must configure the following legal specifications with formal legal review:
            </p>
            <ul className="text-xs text-amber-900/80 dark:text-amber-200/80 space-y-1.5 list-disc pl-5">
              <li><strong>Governing Law &amp; Jurisdiction:</strong> Insert the specific country, state, or province governing dispute resolution.</li>
              <li><strong>Arbitration &amp; Class Action Waiver:</strong> Specify mandatory arbitration procedures or local court venue requirements.</li>
              <li><strong>Notice / Legal Contact Address:</strong> Provide the official registered legal agent, business address, and contact email.</li>
              <li><strong>Commercial SLAs:</strong> If offering paid or enterprise tiers, append formal Service Level Agreements (uptime guarantees and liability caps).</li>
            </ul>
          </section>
        </div>
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-xs text-gray-600 dark:text-gray-300">
        <div className="max-w-4xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>DocForge &copy; 2026 &bull; Private &amp; Secure Online PDF Utilities</p>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Privacy Policy
            </Link>
            <Link href="/tools" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              All Tools
            </Link>
            <Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Dashboard
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
