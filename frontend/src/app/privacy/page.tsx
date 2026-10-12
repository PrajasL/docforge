import React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/navbar";
import { ShieldCheck, Clock, FileLock, Server, AlertTriangle, ArrowLeft } from "lucide-react";
import { getSiteUrl } from "@/config/tools-seo";

export const metadata: Metadata = {
  title: "Privacy Policy — DocForge",
  description:
    "Privacy policy and data processing disclosure for DocForge. Learn how files are processed, stored temporarily, and automatically deleted after 2 hours.",
  alternates: {
    canonical: `${getSiteUrl()}/privacy`,
  },
  openGraph: {
    title: "Privacy Policy — DocForge",
    description:
      "Privacy policy and data processing disclosure for DocForge. Truthful disclosure of temporary storage, 2-hour automated purge, and zero third-party APIs.",
    url: `${getSiteUrl()}/privacy`,
    siteName: "DocForge",
    locale: "en_US",
    type: "website",
  },
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Skip to Main Content Accessibility Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 z-50 px-4 py-2 bg-blue-600 text-white rounded-md shadow-lg outline-none ring-2 ring-offset-2 ring-blue-500"
      >
        Skip to main content
      </a>

      <Navbar currentToolName="Privacy Policy" badge="Legal" />

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
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Transparent Data Processing Policy</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            Privacy Policy
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Effective Date: October 11, 2026 &bull; Version 1.0 (Architecture Aligned)
          </p>
        </header>

        <div className="prose prose-blue dark:prose-invert max-w-none space-y-10 text-gray-700 dark:text-gray-300 leading-relaxed">
          {/* Key Principles Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 not-prose">
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                <Clock className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">2-Hour Auto-Purge</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                Files and metadata are automatically and permanently deleted 2 hours after creation.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
                <Server className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Zero Third-Party APIs</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                Files are processed locally on DocForge dedicated workers using permissive open-source engines.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
                <FileLock className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">Ephemeral Passwords</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                PDF protect/unlock passwords live solely in transient memory and are deleted immediately upon pickup.
              </p>
            </div>
          </div>

          {/* Section 1 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              1. Information We Collect and Process
            </h2>
            <p>
              DocForge is designed around privacy-by-design principles. We do not require account registration, passwords, credit cards, or personal profiles to use our utilities.
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Uploaded Documents:</strong> Files you upload (PDF documents and JPEG images) to execute conversion, compression, merging, or organization operations.
              </li>
              <li>
                <strong>Anonymous Session Tokens:</strong> An ephemeral UUID session identifier (passed via the <code>X-Session-Id</code> header) generated by your client to segregate your jobs and prevent other users from accessing your uploads or downloads.
              </li>
              <li>
                <strong>Technical Request Metadata:</strong> Standard HTTP request logs (IP address, user-agent, request timestamps, and response statuses) required for abuse prevention, rate limiting, and infrastructure diagnostics.
              </li>
            </ul>
          </section>

          {/* Section 2 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              2. How Document Processing Works (Truthful Architecture Disclosure)
            </h2>
            <p>
              Unlike tools that falsely claim 100% in-browser processing while secretly streaming documents to cloud APIs, DocForge operates transparently:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Dedicated Processing Pipeline:</strong> Documents are transmitted securely over TLS to DocForge&apos;s background worker cluster. Conversions, compression, rotations, and security operations execute on our isolated background workers using audited permissive open-source libraries (<code>pypdf</code>, <code>pikepdf</code>, <code>reportlab</code>, <code>pypdfium2</code>, and <code>Pillow</code>).
              </li>
              <li>
                <strong>Client-Side Rendering:</strong> Real-time page thumbnail rendering for the Organize PDF tool executes in your web browser using our bundled, local PDF.js worker. The final PDF reorganization is compiled on DocForge&apos;s dedicated worker nodes.
              </li>
              <li>
                <strong>No Third-Party Conversion APIs:</strong> Your documents are never sent, sold, shared, or proxied to external conversion vendors, AI models (OpenAI, Anthropic, Google), or commercial PDF SaaS APIs.
              </li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              3. Data Retention &amp; Automated 2-Hour Purge Policy
            </h2>
            <p>
              DocForge enforces a strict, automated data expiration lifecycle (TTL: 7,200 seconds / 2 hours):
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Temporary Storage:</strong> Uploaded input files and processed output files are temporarily stored in encrypted S3-compatible object storage (e.g., Cloudflare R2 or MinIO) using date-partitioned storage keys.
              </li>
              <li>
                <strong>Automated Deletion:</strong> An automated background scheduler (Celery Beat) runs periodic cleanup sweeps every 15 minutes. Any job record, input file, and output file older than <strong>two (2) hours</strong> is permanently and irreversibly purged from object storage and database tables.
              </li>
              <li>
                <strong>Zero Long-Term Archives:</strong> DocForge does not maintain backup archives or long-term snapshots of user-uploaded files. Once deleted, files cannot be recovered by either you or DocForge operators.
              </li>
            </ul>
          </section>

          {/* Section 4 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              4. File Validation, Antivirus and Malware Scanning
            </h2>
            <p>
              To protect our users and infrastructure against unauthorized uploads and malicious content:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Default Validation:</strong> All uploaded files undergo strict MIME-type inspection, binary magic-byte verification, and document format checks before processing begins.
              </li>
              <li>
                <strong>Optional ClamAV Integration:</strong> In deployments where ClamAV antivirus scanning is enabled by the operator, files are streamed over TCP directly through an asynchronous ClamAV daemon (via standard INSTREAM protocol).
              </li>
              <li>
                <strong>Threat Response:</strong> If a malicious payload, suspicious signature, or corrupt structure is detected, the file is rejected with an HTTP 400 error and immediately purged from storage.
              </li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              5. Encryption and Password Security
            </h2>
            <p>
              When using password-protected features (Protect PDF and Unlock PDF):
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                User passwords are used strictly to encrypt (AES-256) or decrypt document structures.
              </li>
              <li>
                Passwords are held in ephemeral Redis memory only for the brief duration required for a worker to start the task, and are wiped immediately upon pickup.
              </li>
              <li>
                Passwords are never stored in PostgreSQL databases, job summaries, or persistent application log files.
              </li>
            </ul>
          </section>

          {/* Section 6 */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-800 pb-2">
              6. Telemetry and Error Scrubbing Guarantees
            </h2>
            <p>
              When error monitoring (e.g. Sentry) is enabled by the operator:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                Strict sanitization filters (<code>sentry_before_send</code>) intercept every telemetry payload before it leaves the server.
              </li>
              <li>
                Authorization tokens, Session IDs, Cookie headers, and proxy credentials are automatically redacted.
              </li>
              <li>
                Request bodies containing document uploads or binary blobs are dropped to <code>[FILTERED_UPLOAD_PAYLOAD]</code>.
              </li>
              <li>
                URLs and breadcrumbs containing presigned S3 signatures, credentials, or security tokens are scrubbed to prevent exposure.
              </li>
            </ul>
          </section>

          {/* Section 7 - Operator Action Items */}
          <section className="space-y-4 not-prose p-6 rounded-2xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
              <h2 className="text-lg">7. Operator Notice: Production Legal Customization Required</h2>
            </div>
            <p className="text-sm text-amber-900/90 dark:text-amber-200/90 leading-relaxed">
              This Privacy Policy reflects the authentic technical architecture of the DocForge application. Prior to commercial deployment and public user onboarding, the deployment owner must complete the following items with qualified legal counsel:
            </p>
            <ul className="text-xs text-amber-900/80 dark:text-amber-200/80 space-y-1.5 list-disc pl-5">
              <li><strong>Legal Entity &amp; Operator:</strong> Specify the registered operating entity name and jurisdiction.</li>
              <li><strong>Contact &amp; DPO Email:</strong> Insert the designated privacy/support email address.</li>
              <li><strong>Governing Law:</strong> Define the applicable regional privacy legislation (e.g., GDPR, CCPA/CPRA, PIPEDA).</li>
              <li><strong>Data Processing Agreements:</strong> Execute DPAs with chosen cloud hosting and storage providers (e.g., Cloudflare R2, AWS, or self-hosted datacenter).</li>
            </ul>
          </section>
        </div>
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-xs text-gray-600 dark:text-gray-300">
        <div className="max-w-4xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>DocForge &copy; 2026 &bull; Private &amp; Secure Online PDF Utilities</p>
          <div className="flex items-center gap-4">
            <Link href="/terms" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Terms of Service
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
