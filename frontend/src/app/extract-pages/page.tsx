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
  FileSpreadsheet,
  Layers,
  Copy,
  Info,
} from "lucide-react";
import { ToolSeoSection } from "@/components/tool-seo-section";
import { getToolSeoData } from "@/config/tools-seo";


interface SelectedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  detectedPages?: number | null;
}

interface ResultData {
  jobId: string;
  filename: string;
  sizeBytes: number;
  pageCount?: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export async function countPdfPages(file: File): Promise<number | null> {
  try {
    if (!file || typeof file.arrayBuffer !== "function") return null;
    const arrayBuffer = await file.arrayBuffer();

    // 1. First attempt PDF.js parse (handles compressed object streams, xref streams, incremental updates)
    if (typeof window !== "undefined") {
      try {
        const pdfjs = await import("pdfjs-dist");
        const getDocument = pdfjs.getDocument || (pdfjs as any).default?.getDocument;
        const GlobalWorkerOptions = pdfjs.GlobalWorkerOptions || (pdfjs as any).default?.GlobalWorkerOptions;
        if (GlobalWorkerOptions) {
          GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        }
        if (getDocument) {
          // Pass a cloned buffer copy to prevent detaching original arrayBuffer on worker transfer
          const bufferCopy = arrayBuffer.slice(0);
          const loadingTask = getDocument({
            data: new Uint8Array(bufferCopy),
            isEvalSupported: false,
            enableXfa: false,
            disableRange: true,
            disableStream: true,
            disableAutoFetch: true,
          } as any);
          const doc = await loadingTask.promise;
          if (doc && typeof doc.numPages === "number" && doc.numPages > 0) {
            return doc.numPages;
          }
        }
      } catch {
        // Fallback to byte analysis if PDF.js fails (e.g. encrypted or worker network unavailable)
      }
    }

    // 2. Fallback heuristic on raw bytes
    const text = new TextDecoder("latin1").decode(arrayBuffer);
    const hasObjStm = text.includes("/ObjStm");

    const matches = text.match(/\/Type\s*\/Page\b(?![sS])/g);
    if (!hasObjStm && matches && matches.length > 0) {
      return matches.length;
    }

    const rootCountMatch =
      text.match(/\/Type\s*\/Pages\b[\s\S]*?\/Count\s+(\d+)/) ||
      text.match(/\/Count\s+(\d+)[\s\S]*?\/Type\s*\/Pages\b/) ||
      text.match(/\/Count\s+(\d+)/);

    if (rootCountMatch && rootCountMatch[1]) {
      const parsed = parseInt(rootCountMatch[1], 10);
      if (parsed > 0) return parsed;
    }

    if (matches && matches.length > 0) {
      return matches.length;
    }
  } catch {
    return null;
  }
  return null;
}

export const detectPdfPageCount = countPdfPages;

export default function ExtractPagesPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [extractAll, setExtractAll] = useState<boolean>(false);
  const [pageRanges, setPageRanges] = useState<string>("1-2");
  const [outputFilename, setOutputFilename] = useState<string>("");

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

  useEffect(() => {
    if (errorMessage && typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [errorMessage]);

  const handleFileAdded = (incoming: FileList | File[]) => {
    if (!incoming || incoming.length === 0) return;
    const file = incoming[0];

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage(`Skipped non-PDF file: ${file.name}. Only PDF files are supported.`);
      return;
    }

    setErrorMessage(null);
    const baseName = file.name.replace(/\.pdf$/i, "");
    setOutputFilename(`extracted_${baseName}.pdf`);

    setSelectedFile({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      detectedPages: null,
    });

    // Detect page count asynchronously in background
    detectPdfPageCount(file).then((detected) => {
      if (detected !== null) {
        setSelectedFile((prev) => (prev && prev.name === file.name ? { ...prev, detectedPages: detected } : prev));
        if (detected === 1) {
          setPageRanges("1");
        } else {
          setPageRanges(`1-${Math.min(2, detected)}`);
        }
      }
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
    setExtractAll(false);
    setPageRanges("1-2");
    setOutputFilename("");
    setErrorMessage(null);
    setStage("idle");
    setResult(null);
    setProgress(0);
    setStatusMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const startExtraction = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }

    if (!extractAll && !pageRanges.trim()) {
      setErrorMessage("Please specify page numbers or ranges to extract (e.g. '1, 3-5, 8').");
      return;
    }

    // Client-side out-of-bounds check if page count is known
    if (!extractAll && selectedFile.detectedPages) {
      const parts = pageRanges.split(",").map((p) => p.trim()).filter(Boolean);
      for (const part of parts) {
        if (part.includes("-")) {
          const [s, e] = part.split("-").map((v) => parseInt(v.trim(), 10));
          if (!isNaN(e) && e > selectedFile.detectedPages) {
            setErrorMessage(
              `Page range '${part}' exceeds document's total page count (${selectedFile.detectedPages}).`
            );
            return;
          }
          if (!isNaN(s) && !isNaN(e) && s > e) {
            setErrorMessage(`Start page (${s}) cannot be greater than end page (${e}) in range '${part}'.`);
            return;
          }
        } else {
          const p = parseInt(part, 10);
          if (!isNaN(p) && p > selectedFile.detectedPages) {
            setErrorMessage(
              `Page ${p} is out of bounds for a document with ${selectedFile.detectedPages} pages.`
            );
            return;
          }
        }
      }
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing extraction pipeline...");

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
          tool: "extract_pages",
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

      const createJson = await createRes.json();
      const jobId = createJson.data.job.id;
      const uploadItem = createJson.data.uploads[0];

      setProgress(25);
      setStatusMessage("Uploading document to secure processing pipeline...");

      // Step 2: Upload file via direct API endpoint
      const uploadRes = await fetch(
        `${apiUrl}/api/v1/jobs/${jobId}/files/${uploadItem.file_id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/pdf",
            "X-Session-Id": sessionId,
          },
          body: selectedFile.file,
        }
      );

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to upload file (${uploadRes.status})`);
      }

      setProgress(50);
      setStatusMessage("Configuring page extraction parameters...");

      // Step 3: Start job with extraction config
      const finalName = outputFilename.trim() || `extracted_${selectedFile.name}`;
      const configPayload: Record<string, any> = {
        extract_all: extractAll,
        pages: extractAll ? "all" : pageRanges.trim(),
        output_filename: finalName,
      };

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: configPayload,
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to start extraction job (${startRes.status})`);
      }

      setStage("processing");
      setStatusMessage("Extracting selected pages into unified PDF...");

      // Step 4: Poll job status
      let attempts = 0;
      const maxAttempts = 60;

      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const pollRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, {
            headers: {
              "X-Session-Id": sessionId,
            },
          });

          if (!pollRes.ok) {
            clearInterval(pollInterval);
            throw new Error(`Failed to check job progress (${pollRes.status})`);
          }

          const pollData = await pollRes.json();
          const job = pollData.data?.job || pollData.data;
          const status = (job?.status || "").toUpperCase();

          if (status === "PROCESSING") {
            const currentProgress = job.progress > 50 ? job.progress : 50 + attempts * 4;
            setProgress(Math.min(currentProgress, 95));
            setStatusMessage("Compiling extracted PDF and preserving page properties...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Pages extracted successfully!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              pageCount: resFile?.page_count,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Extraction processing failed on server.");
          } else if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage("Operation timed out waiting for worker processing.");
          }
        } catch (pollErr: unknown) {
          clearInterval(pollInterval);
          setStage("error");
          const msg = pollErr instanceof Error ? pollErr.message : "Error checking job status.";
          setErrorMessage(msg);
        }
      }, 1000);
    } catch (err: unknown) {
      setStage("error");
      const msg = err instanceof Error ? err.message : "Unexpected error during page extraction.";
      setErrorMessage(msg);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const sessionId = sessionIdRef.current;

    try {
      const res = await fetch(`${apiUrl}/api/v1/jobs/${result.jobId}/download`, {
        headers: {
          "X-Session-Id": sessionId,
        },
      });

      if (!res.ok) {
        throw new Error(`Download request failed (${res.status})`);
      }

      const json = await res.json();
      const downloadUrl = json.data.download_url;

      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to download extracted PDF.";
      setErrorMessage(msg);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Extract Pages" icon={FileSpreadsheet} iconBgColor="bg-violet-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner Info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Extract Pages from PDF
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Extract specific pages or page ranges and save them into a new, unified PDF document in your exact requested order.
          </p>
        </div>

        {/* Global Error Banner */}
        {errorMessage && (
          <div
            id="global-error-banner"
            role="alert"
            className="p-4 rounded-xl bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 flex items-start space-x-3 text-red-800 dark:text-red-200 animate-in fade-in duration-200"
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm font-medium">{errorMessage}</div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-600 dark:text-red-400 hover:opacity-80 text-xs font-semibold px-2 py-1 rounded"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Dropzone (if no file chosen) */}
        {!selectedFile && (
          <Card
            className={`border-2 border-dashed transition-all duration-200 ${
              isDragging
                ? "border-teal-500 bg-teal-50/50 dark:bg-teal-950/20 scale-[1.01]"
                : "border-gray-300 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="w-16 h-16 rounded-full bg-teal-50 dark:bg-teal-950/40 text-teal-600 dark:text-teal-400 flex items-center justify-center mb-4">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                Choose a PDF to extract pages from
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
                Drag and drop your PDF here, or select a file from your computer.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                id="pdf-upload-input"
                aria-label="Upload PDF file to extract pages"
                onChange={(e) => {
                  if (e.target.files) handleFileAdded(e.target.files);
                }}
              />
              <Button
                id="select-file-btn"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="bg-teal-700 hover:bg-teal-800 text-white shadow-sm"
              >
                Select PDF File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Active Workspace / Configuration */}
        {selectedFile && (
          <div className="space-y-6">
            {/* Selected File Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="truncate">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {selectedFile.name}
                    </p>
                    <div className="flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      <span>{formatBytes(selectedFile.size)}</span>
                      {selectedFile.detectedPages !== null && selectedFile.detectedPages !== undefined && (
                        <span
                          id="detected-pages-badge"
                          className="inline-flex items-center px-2 py-0.5 rounded-full font-medium bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border border-teal-200/50"
                        >
                          {selectedFile.detectedPages} pages detected
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                {stage !== "uploading" && stage !== "processing" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearSelection}
                    className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                    title="Change file"
                  >
                    <Trash2 className="w-4 h-4 mr-1.5" />
                    Change File
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Page Extraction Settings Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardHeader className="pb-4 border-b border-gray-100 dark:border-gray-800">
                <CardTitle className="text-base font-semibold flex items-center">
                  <Layers className="w-4 h-4 mr-2 text-teal-600" />
                  Extract Mode &amp; Page Range
                </CardTitle>
                <CardDescription className="text-xs">
                  Choose specific pages, custom ranges, or extract the entire document.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-5">
                {/* Extraction Mode Toggle */}
                <div className="flex items-center space-x-4">
                  <button
                    type="button"
                    onClick={() => setExtractAll(false)}
                    className={`flex-1 p-3 rounded-lg border text-left transition-all ${
                      !extractAll
                        ? "border-teal-500 bg-teal-50/40 dark:bg-teal-950/30 text-teal-900 dark:text-teal-100 ring-1 ring-teal-500"
                        : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    <div className="text-xs font-semibold uppercase tracking-wider mb-0.5">
                      Specific Pages &amp; Ranges
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      e.g. 1, 3-5, 8 in custom order
                    </div>
                  </button>

                  <button
                    type="button"
                    id="extract-all-toggle-btn"
                    onClick={() => setExtractAll(true)}
                    className={`flex-1 p-3 rounded-lg border text-left transition-all ${
                      extractAll
                        ? "border-teal-500 bg-teal-50/40 dark:bg-teal-950/30 text-teal-900 dark:text-teal-100 ring-1 ring-teal-500"
                        : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    <div className="text-xs font-semibold uppercase tracking-wider mb-0.5">
                      Extract All Pages
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Combine all {selectedFile.detectedPages ?? ""} pages into one file
                    </div>
                  </button>
                </div>

                {/* Specific Pages Input Field */}
                {!extractAll && (
                  <div className="space-y-1.5 animate-in fade-in duration-200">
                    <label
                      htmlFor="page-ranges-input"
                      className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300 flex items-center justify-between"
                    >
                      <span>Pages to Extract</span>
                      {selectedFile.detectedPages && (
                        <span className="text-gray-400 font-normal lowercase">
                          (valid: 1 to {selectedFile.detectedPages})
                        </span>
                      )}
                    </label>
                    <input
                      id="page-ranges-input"
                      type="text"
                      value={pageRanges}
                      onChange={(e) => setPageRanges(e.target.value)}
                      placeholder="e.g. 1, 3-5, 8"
                      disabled={stage === "uploading" || stage === "processing" || stage === "completed"}
                      className="w-full px-3 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:opacity-50"
                    />
                    <div className="flex flex-wrap gap-2 pt-1">
                      <span className="text-xs text-gray-400 self-center">Presets:</span>
                      <button
                        type="button"
                        onClick={() => setPageRanges("1")}
                        className="text-xs px-2 py-0.5 rounded bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        First Page
                      </button>
                      {selectedFile.detectedPages && selectedFile.detectedPages >= 2 && (
                        <button
                          type="button"
                          onClick={() => setPageRanges(`1-${Math.min(3, selectedFile.detectedPages!)}`)}
                          className="text-xs px-2 py-0.5 rounded bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                        >
                          1-{Math.min(3, selectedFile.detectedPages)}
                        </button>
                      )}
                      {selectedFile.detectedPages && (
                        <button
                          type="button"
                          onClick={() => setPageRanges(String(selectedFile.detectedPages))}
                          className="text-xs px-2 py-0.5 rounded bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                        >
                          Last Page ({selectedFile.detectedPages})
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Output Filename */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="output-filename-input"
                    className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300"
                  >
                    Output Filename (Optional)
                  </label>
                  <input
                    id="output-filename-input"
                    type="text"
                    value={outputFilename}
                    onChange={(e) => setOutputFilename(e.target.value)}
                    placeholder="extracted_document.pdf"
                    disabled={stage === "uploading" || stage === "processing" || stage === "completed"}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:opacity-50"
                  />
                </div>

                {/* Information Callout */}
                <div className="p-3.5 rounded-lg bg-teal-50 dark:bg-teal-950/30 border border-teal-200/70 dark:border-teal-800/60 text-xs text-teal-800 dark:text-teal-300 flex items-start space-x-2">
                  <Info className="w-4 h-4 mr-1 flex-shrink-0 mt-0.5 text-teal-600" />
                  <p className="leading-relaxed">
                    Pages are extracted in the exact order you specify into a single output PDF. Original page dimensions, orientation, and content streams are preserved.
                  </p>
                </div>

                {/* Action Trigger Button */}
                {stage !== "completed" && (
                  <Button
                    id="extract-submit-btn"
                    onClick={startExtraction}
                    disabled={stage === "uploading" || stage === "processing" || (!extractAll && !pageRanges.trim())}
                    className="w-full bg-teal-600 hover:bg-teal-700 text-white shadow-sm flex items-center justify-center space-x-2 py-2.5 font-medium"
                  >
                    {stage === "uploading" || stage === "processing" ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                        <span>Processing Extraction...</span>
                      </>
                    ) : (
                      <>
                        <Layers className="w-4 h-4 mr-2" />
                        <span>Extract Pages</span>
                      </>
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Progress / Status Bar */}
            {(stage === "uploading" || stage === "processing") && (
              <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm animate-in fade-in">
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span className="text-gray-600 dark:text-gray-300 flex items-center">
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin text-teal-600" />
                      {statusMessage}
                    </span>
                    <span className="text-teal-600 font-semibold">{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-teal-600 h-full transition-all duration-300 rounded-full"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Success / Result View */}
            {stage === "completed" && result && (
              <Card className="bg-white dark:bg-gray-900 border-emerald-200 dark:border-emerald-800/60 shadow-md animate-in fade-in duration-300">
                <CardHeader className="bg-emerald-50/50 dark:bg-emerald-950/20 border-b border-emerald-100 dark:border-emerald-900/50 pb-4">
                  <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-300">
                    <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                    <CardTitle className="text-base font-bold">
                      Pages Successfully Extracted!
                    </CardTitle>
                  </div>
                  <CardDescription className="text-xs text-emerald-800/80 dark:text-emerald-300/80">
                    Your extracted pages have been compiled into a unified PDF document and are ready for download.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800">
                    <div>
                      <span className="text-xs text-gray-500 uppercase tracking-wider block">
                        Filename
                      </span>
                      <span className="text-sm font-semibold truncate block mt-0.5">
                        {result.filename}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500 uppercase tracking-wider block">
                        Pages Extracted
                      </span>
                      <span className="text-sm font-semibold block mt-0.5">
                        {result.pageCount ?? "Unknown"} Pages
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500 uppercase tracking-wider block">
                        Output Size
                      </span>
                      <span className="text-sm font-semibold block mt-0.5">
                        {formatBytes(result.sizeBytes)}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3 pt-2">
                    <Button
                      id="download-result-btn"
                      onClick={handleDownload}
                      className="flex-1 bg-teal-600 hover:bg-teal-700 text-white shadow-sm flex items-center justify-center space-x-2 py-2.5 font-medium"
                    >
                      <Download className="w-4 h-4 mr-1.5" />
                      <span>Download Extracted PDF</span>
                    </Button>
                    <Button
                      id="extract-another-btn"
                      variant="outline"
                      onClick={clearSelection}
                      className="border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <RefreshCw className="w-4 h-4 mr-1.5" />
                      Extract More Pages
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("extract-pages")!} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-600 dark:text-gray-400">
        DocForge PDF Platform &bull; Phase 2 PDF Tools &bull; Single Document Page Extraction
      </footer>
    </div>
  );
}
