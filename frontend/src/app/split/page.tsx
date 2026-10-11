"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { ToolHeader } from "@/components/tool-header";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Download,
  ArrowLeft,
  RefreshCw,
  Scissors,
  Archive,
  Layers,
  Sparkles,
} from "lucide-react";
import { ToolSeoSection } from "@/components/tool-seo-section";
import { getToolSeoData } from "@/config/tools-seo";


interface SelectedFile {
  id: string;
  file: File;
  name: string;
  size: number;
}

interface ResultData {
  jobId: string;
  filename: string;
  sizeBytes: number;
  fileCount?: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type SplitMode = "ranges" | "every_page";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function SplitPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [mode, setMode] = useState<SplitMode>("ranges");
  const [ranges, setRanges] = useState<string>("1-2, 3-4");
  const [outputFilename, setOutputFilename] = useState<string>("split_documents.zip");
  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResultData | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      let sid = sessionStorage.getItem("docforge_session_id");
      if (!sid) {
        sid = crypto.randomUUID();
        sessionStorage.setItem("docforge_session_id", sid);
      }
      sessionIdRef.current = sid;
    }
  }, []);

  const handleFileAdded = (incoming: FileList | File[]) => {
    if (!incoming || incoming.length === 0) return;
    const file = incoming[0];

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage(`Skipped non-PDF file: ${file.name}. Only PDF files are supported.`);
      return;
    }

    setErrorMessage(null);
    setSelectedFile({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileAdded(e.dataTransfer.files);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    setStage("idle");
    setResult(null);
  };

  const startSplit = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file to split.");
      return;
    }

    if (mode === "ranges" && !ranges.trim()) {
      setErrorMessage("Please specify at least one page range (e.g. '1-3, 4-6').");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing split job...");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const sessionId = sessionIdRef.current;

    try {
      // Step 1: Create job in backend
      const createRes = await fetch(`${apiUrl}/api/v1/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          tool: "split",
          files: [
            {
              name: selectedFile.name,
              size: selectedFile.size,
              content_type: "application/pdf",
            },
          ],
          config: {},
        }),
      });

      if (!createRes.ok) {
        const errJson = await createRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to create job (${createRes.status})`);
      }

      const createData = await createRes.json();
      const jobId = createData.data.job.id;
      const uploadFileId = createData.data.uploads[0].file_id;

      // Step 2: Upload file binary
      setStatusMessage("Uploading document...");
      setProgress(25);

      const uploadRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/files/${uploadFileId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/pdf",
          "X-Session-Id": sessionId,
        },
        body: await selectedFile.file.arrayBuffer(),
      });

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed uploading ${selectedFile.name}`);
      }

      // Step 3: Start job
      setStage("processing");
      setStatusMessage("Queueing worker task...");
      setProgress(50);

      const splitConfig: Record<string, any> = {
        mode,
        output_filename: outputFilename.trim() || "split_documents.zip",
      };
      if (mode === "ranges") {
        splitConfig.ranges = ranges.trim();
      }

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: splitConfig,
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to start split job`);
      }

      // Step 4: Poll job status
      setStatusMessage("Splitting pages and packaging archive...");
      let isDone = false;
      const maxAttempts = 60;
      let attempts = 0;

      while (!isDone && attempts < maxAttempts) {
        attempts++;
        await new Promise((r) => setTimeout(r, 800));

        const pollRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, {
          headers: { "X-Session-Id": sessionId },
        });

        if (!pollRes.ok) continue;

        const pollData = await pollRes.json();
        const job = pollData.data.job;

        if (job.status === "PROCESSING") {
          const workerProgress = Math.max(50, Math.min(95, job.progress));
          setProgress(workerProgress);
          setStatusMessage(`Extracting pages (${workerProgress}%)...`);
        } else if (job.status === "COMPLETED") {
          isDone = true;
          setProgress(100);
          setStage("completed");
          setResult({
            jobId: job.id,
            filename: job.result_file?.original_name || "split_documents.zip",
            sizeBytes: job.result_file?.size_bytes || 0,
            fileCount: job.result_file?.file_count,
          });
          setStatusMessage("Split complete!");
          return;
        } else if (job.status === "FAILED") {
          throw new Error(job.error_message || "Job processing failed in worker.");
        }
      }

      if (!isDone) {
        throw new Error("Job processing timed out. Please try again.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setErrorMessage(msg);
      setStage("error");
    }
  };

  const handleDownload = async () => {
    if (!result?.jobId) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/jobs/${result.jobId}/download`, {
        headers: { "X-Session-Id": sessionIdRef.current },
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || "Failed to generate download URL.");
      }

      const json = await res.json();
      const downloadUrl = json.data.download_url;

      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Download failed.";
      setErrorMessage(msg);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Split PDF" icon={Scissors} iconBgColor="bg-purple-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Page Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            Split PDF Document
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm sm:text-base">
            Extract custom page ranges or separate every single page into individual documents packaged in a ZIP archive.
          </p>
        </div>

        {/* Global Error Banner */}
        {errorMessage && (
          <div
            role="alert"
            className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-900 dark:text-red-200 text-sm flex items-start space-x-3 shadow-sm animate-in fade-in"
          >
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium">Error</p>
              <p className="text-red-700 dark:text-red-300 mt-0.5">{errorMessage}</p>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-500 hover:text-red-700 dark:hover:text-red-300 text-xs font-semibold px-2 py-1"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* COMPLETED STATE */}
        {stage === "completed" && result && (
          <Card className="border-green-300 dark:border-green-800 bg-green-50/40 dark:bg-green-950/20 shadow-md">
            <CardContent className="pt-8 pb-8 text-center space-y-5">
              <div className="w-16 h-16 rounded-2xl bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400 flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <div className="space-y-1">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">PDF Successfully Split!</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Your extracted documents have been securely bundled into a ZIP archive.
                </p>
              </div>

              {/* Result Meta Details */}
              <div className="inline-flex items-center gap-4 px-4 py-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-300">
                <span className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                  <Archive className="w-3.5 h-3.5 text-purple-600" />
                  {result.filename}
                </span>
                <span>&bull;</span>
                <span>{formatBytes(result.sizeBytes)}</span>
                {result.fileCount && (
                  <>
                    <span>&bull;</span>
                    <span>{result.fileCount} PDF files created</span>
                  </>
                )}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button
                  id="download-split-zip-btn"
                  onClick={handleDownload}
                  size="lg"
                  className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold gap-2 shadow-lg shadow-green-600/20"
                >
                  <Download className="w-5 h-5" />
                  Download ZIP Archive
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={clearSelection}
                  className="w-full sm:w-auto"
                >
                  Split Another PDF
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PROCESSING & UPLOADING PROGRESS STATE */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-purple-200 dark:border-purple-900/50 shadow-md">
            <CardContent className="py-10 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto animate-pulse">
                <RefreshCw className="w-7 h-7 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  {stage === "uploading" ? "Uploading Document" : "Processing Split"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{statusMessage}</p>
              </div>

              {/* Progress Bar */}
              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-purple-600 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 font-medium">
                  <span>{progress}% complete</span>
                  <span>{stage === "uploading" ? "Stage 1/2" : "Stage 2/2"}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* IDLE / CONFIGURATION STATE */}
        {stage !== "completed" && stage !== "uploading" && stage !== "processing" && (
          <div className="space-y-6">
            {/* File Dropzone (if no file chosen) */}
            {!selectedFile ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
                  isDragging
                    ? "border-purple-500 bg-purple-50/60 dark:bg-purple-950/30 scale-[1.01]"
                    : "border-gray-300 dark:border-gray-800 hover:border-purple-400 hover:bg-gray-50/50 dark:hover:bg-gray-900/40"
                }`}
              >
                <input
                  id="split-file-input"
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  aria-label="Upload PDF file to split"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileAdded(e.target.files);
                      e.target.value = "";
                    }
                  }}
                />

                <div className="flex flex-col items-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 flex items-center justify-center shadow-inner">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-base font-semibold text-gray-800 dark:text-gray-200">
                      Choose a PDF file or drag & drop it here
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Select 1 PDF file to extract page ranges or separate individual pages.
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="mt-2 pointer-events-none"
                  >
                    Browse PDF File
                  </Button>
                </div>
              </div>
            ) : (
              /* Selected File Card */
              <Card className="shadow-sm border-purple-200/60 dark:border-purple-900/40">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <FileText className="w-4 h-4 text-purple-600" /> Selected Document
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Ready for splitting. Configure your page ranges below.
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearSelection}
                    className="text-xs h-8 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20 gap-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Change File
                  </Button>
                </CardHeader>

                <CardContent className="space-y-4 pt-1">
                  <div
                    data-testid="selected-file-item"
                    className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200/80 dark:border-gray-800"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <FileText className="w-5 h-5 text-red-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {selectedFile.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatBytes(selectedFile.size)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Splitting Mode Controls */}
                  <div className="space-y-3 pt-2">
                    <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block">
                      Splitting Mode
                    </label>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {/* Mode 1: Custom Ranges */}
                      <button
                        type="button"
                        onClick={() => setMode("ranges")}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                          mode === "ranges"
                            ? "border-purple-600 bg-purple-50/50 dark:bg-purple-950/30 ring-1 ring-purple-600 text-purple-950 dark:text-purple-100"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
                        }`}
                      >
                        <div className="font-semibold text-sm flex items-center justify-between">
                          <span>Custom Page Ranges</span>
                          {mode === "ranges" && <Sparkles className="w-4 h-4 text-purple-600" />}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Extract specific page spans (e.g. 1-3, 4-6, 7-9)
                        </p>
                      </button>

                      {/* Mode 2: Every Page */}
                      <button
                        type="button"
                        onClick={() => setMode("every_page")}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                          mode === "every_page"
                            ? "border-purple-600 bg-purple-50/50 dark:bg-purple-950/30 ring-1 ring-purple-600 text-purple-950 dark:text-purple-100"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
                        }`}
                      >
                        <div className="font-semibold text-sm flex items-center justify-between">
                          <span>Extract Every Page</span>
                          {mode === "every_page" && <Sparkles className="w-4 h-4 text-purple-600" />}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Separate each page into its own individual PDF
                        </p>
                      </button>
                    </div>

                    {/* Range Input Field (when ranges mode is selected) */}
                    {mode === "ranges" && (
                      <div className="space-y-1.5 pt-2">
                        <label
                          htmlFor="page-ranges-input"
                          className="text-xs font-medium text-gray-700 dark:text-gray-300 flex items-center justify-between"
                        >
                          <span>Page Ranges</span>
                          <span className="text-[11px] text-gray-400">Comma-separated ranges or pages</span>
                        </label>
                        <input
                          id="page-ranges-input"
                          type="text"
                          value={ranges}
                          onChange={(e) => setRanges(e.target.value)}
                          placeholder="e.g. 1-3, 4-6, 7-9"
                          className="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        />
                        <div className="flex gap-2 text-[11px] text-gray-400 pt-0.5">
                          <span>Quick presets:</span>
                          <button
                            type="button"
                            onClick={() => setRanges("1-2, 3-4")}
                            className="underline hover:text-purple-600"
                          >
                            1-2, 3-4
                          </button>
                          <span>&bull;</span>
                          <button
                            type="button"
                            onClick={() => setRanges("1, 2-3")}
                            className="underline hover:text-purple-600"
                          >
                            1, 2-3
                          </button>
                          <span>&bull;</span>
                          <button
                            type="button"
                            onClick={() => setRanges("1")}
                            className="underline hover:text-purple-600"
                          >
                            1 (first page)
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Options & Output Filename */}
                  <div className="pt-4 mt-4 border-t border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="w-full sm:w-auto flex items-center space-x-2 text-xs">
                      <label htmlFor="output-zip-filename" className="text-gray-500 font-medium">
                        ZIP Name:
                      </label>
                      <input
                        id="output-zip-filename"
                        type="text"
                        value={outputFilename}
                        onChange={(e) => setOutputFilename(e.target.value)}
                        placeholder="split_documents.zip"
                        className="px-2.5 py-1 text-xs rounded-md bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                    </div>

                    {/* Split Action Button */}
                    <div className="w-full sm:w-auto flex items-center justify-end">
                      <Button
                        id="split-action-btn"
                        onClick={startSplit}
                        className="w-full sm:w-auto bg-purple-600 hover:bg-purple-700 text-white font-semibold gap-2 shadow-md shadow-purple-500/20"
                      >
                        <Scissors className="w-4 h-4" />
                        Split PDF
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("split")!} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-xs text-gray-600 dark:text-gray-400">
        <p>DocForge &copy; 2026 &mdash; High Performance PDF Processing.</p>
      </footer>
    </div>
  );
}
