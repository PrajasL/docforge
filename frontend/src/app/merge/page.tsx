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
  ArrowUp,
  ArrowDown,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Download,
  ArrowLeft,
  RefreshCw,
  Layers,
  GripVertical,
  Plus,
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
  pageCount?: number;
  downloadUrl?: string;
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

export default function MergePdfPage() {
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResultData | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [outputFilename, setOutputFilename] = useState<string>("merged_document.pdf");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    // Generate or retain anonymous session ID
    if (typeof window !== "undefined") {
      let sid = sessionStorage.getItem("docforge_session_id");
      if (!sid) {
        sid = crypto.randomUUID();
        sessionStorage.setItem("docforge_session_id", sid);
      }
      sessionIdRef.current = sid;
    }
  }, []);

  const handleFilesAdded = (incoming: FileList | File[]) => {
    const validPdfs: SelectedFile[] = [];
    const rejected: string[] = [];

    Array.from(incoming).forEach((file) => {
      if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
        validPdfs.push({
          id: crypto.randomUUID(),
          file,
          name: file.name,
          size: file.size,
        });
      } else {
        rejected.push(file.name);
      }
    });

    if (rejected.length > 0) {
      setErrorMessage(`Skipped non-PDF files: ${rejected.join(", ")}`);
    } else {
      setErrorMessage(null);
    }

    setFiles((prev) => [...prev, ...validPdfs]);
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
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    setFiles((prev) => {
      const copy = [...prev];
      const temp = copy[index - 1];
      copy[index - 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const moveDown = (index: number) => {
    if (index === files.length - 1) return;
    setFiles((prev) => {
      const copy = [...prev];
      const temp = copy[index + 1];
      copy[index + 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const clearAll = () => {
    setFiles([]);
    setErrorMessage(null);
    setStage("idle");
    setResult(null);
  };

  const startMerge = async () => {
    if (files.length < 2) {
      setErrorMessage("Please select at least 2 PDF files to merge.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Creating merge job...");

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
          tool: "merge",
          files: files.map((f) => ({
            name: f.name,
            size: f.size,
            content_type: "application/pdf",
          })),
          config: {},
        }),
      });

      if (!createRes.ok) {
        const errJson = await createRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to create job (${createRes.status})`);
      }

      const createData = await createRes.json();
      const jobId = createData.data.job.id;
      const uploads = createData.data.uploads;

      // Step 2: Upload files
      setStatusMessage("Uploading PDF files...");
      for (let i = 0; i < files.length; i++) {
        const item = files[i];
        const uploadMeta = uploads[i];
        const uploadFileId = uploadMeta.file_id;

        const uploadRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/files/${uploadFileId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/pdf",
            "X-Session-Id": sessionId,
          },
          body: await item.file.arrayBuffer(),
        });

        if (!uploadRes.ok) {
          const errJson = await uploadRes.json().catch(() => ({}));
          throw new Error(errJson?.error?.message || `Failed uploading ${item.name}`);
        }

        const uploadPercent = Math.round(10 + (40 * (i + 1)) / files.length);
        setProgress(uploadPercent);
      }

      // Step 3: Start job
      setStage("processing");
      setStatusMessage("Queueing worker task...");
      setProgress(50);

      // Map client file order to upload file IDs
      const fileOrderIds = uploads.map((u: { file_id: string }) => u.file_id);

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: {
            file_order: fileOrderIds,
            output_filename: outputFilename.trim() || "merged_document.pdf",
          },
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to start job processing`);
      }

      // Step 4: Poll job status
      setStatusMessage("Merging pages with background worker...");
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
          setStatusMessage(`Processing pages (${workerProgress}%)...`);
        } else if (job.status === "COMPLETED") {
          isDone = true;
          setProgress(100);
          setStage("completed");
          setResult({
            jobId: job.id,
            filename: job.result_file?.original_name || "merged_document.pdf",
            sizeBytes: job.result_file?.size_bytes || 0,
            pageCount: job.result_file?.page_count,
          });
          setStatusMessage("Merge complete!");
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

      // Trigger browser download
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
      <ToolHeader toolName="Merge PDF" icon={Layers} iconBgColor="bg-blue-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Page Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            Merge PDF Files
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm sm:text-base">
            Combine multiple PDFs into a single unified document in your preferred page order.
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
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">PDFs Successfully Merged!</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Your new unified document is ready for download.
                </p>
              </div>

              {/* Result Meta Details */}
              <div className="inline-flex items-center gap-4 px-4 py-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-300">
                <span className="font-semibold text-gray-900 dark:text-white">{result.filename}</span>
                <span>&bull;</span>
                <span>{formatBytes(result.sizeBytes)}</span>
                {result.pageCount && (
                  <>
                    <span>&bull;</span>
                    <span>{result.pageCount} pages</span>
                  </>
                )}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button
                  id="download-merged-pdf-btn"
                  onClick={handleDownload}
                  size="lg"
                  className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold gap-2 shadow-lg shadow-green-600/20"
                >
                  <Download className="w-5 h-5" />
                  Download Merged PDF
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={clearAll}
                  className="w-full sm:w-auto"
                >
                  Merge More Files
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PROCESSING & UPLOADING PROGRESS STATE */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-blue-200 dark:border-blue-900/50 shadow-md">
            <CardContent className="py-10 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto animate-pulse">
                <RefreshCw className="w-7 h-7 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  {stage === "uploading" ? "Uploading Documents" : "Processing Merge"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{statusMessage}</p>
              </div>

              {/* Progress Bar */}
              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
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

        {/* IDLE / FILE SELECTION STATE */}
        {stage !== "completed" && stage !== "uploading" && stage !== "processing" && (
          <div className="space-y-6">
            {/* Drag & Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
                isDragging
                  ? "border-blue-500 bg-blue-50/60 dark:bg-blue-950/30 scale-[1.01]"
                  : "border-gray-300 dark:border-gray-800 hover:border-blue-400 hover:bg-gray-50/50 dark:hover:bg-gray-900/40"
              }`}
            >
              <input
                id="merge-file-input"
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,application/pdf"
                className="hidden"
                aria-label="Upload PDF files to merge"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFilesAdded(e.target.files);
                    e.target.value = "";
                  }
                }}
              />

              <div className="flex flex-col items-center space-y-3">
                <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shadow-inner">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <p className="text-base font-semibold text-gray-800 dark:text-gray-200">
                    Choose PDF files or drag & drop them here
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Select 2 to 20 PDF files. Reorder files to arrange your document.
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  className="mt-2 pointer-events-none"
                >
                  Browse Files
                </Button>
              </div>
            </div>

            {/* Selected File List with Reordering Controls */}
            {files.length > 0 && (
              <Card className="shadow-sm">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold">
                      Selected Files ({files.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Merge order flows from top (Page 1) to bottom. Use the arrows to reorder.
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-xs h-8 gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add More
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearAll}
                      className="text-xs h-8 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                    >
                      Clear All
                    </Button>
                  </div>
                </CardHeader>

                <CardContent className="space-y-2 pt-1">
                  <div className="space-y-2">
                    {files.map((item, idx) => (
                      <div
                        key={item.id}
                        data-testid={`file-item-${idx}`}
                        className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200/80 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-colors"
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          <span className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-bold flex items-center justify-center flex-shrink-0">
                            {idx + 1}
                          </span>
                          <FileText className="w-5 h-5 text-red-500 flex-shrink-0" />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                              {item.name}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {formatBytes(item.size)}
                            </p>
                          </div>
                        </div>

                        {/* Reorder and Remove Controls */}
                        <div className="flex items-center space-x-1 flex-shrink-0">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => moveUp(idx)}
                            disabled={idx === 0}
                            title="Move up"
                            aria-label={`Move ${item.name} up`}
                            className="h-8 w-8 text-gray-500 hover:text-gray-900 dark:hover:text-white disabled:opacity-30"
                          >
                            <ArrowUp className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => moveDown(idx)}
                            disabled={idx === files.length - 1}
                            title="Move down"
                            aria-label={`Move ${item.name} down`}
                            className="h-8 w-8 text-gray-500 hover:text-gray-900 dark:hover:text-white disabled:opacity-30"
                          >
                            <ArrowDown className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeFile(item.id)}
                            title="Remove file"
                            aria-label={`Remove ${item.name}`}
                            className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Options & Output Filename */}
                  <div className="pt-4 mt-4 border-t border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="w-full sm:w-auto flex items-center space-x-2 text-xs">
                      <label htmlFor="output-filename" className="text-gray-500 font-medium">
                        Output Name:
                      </label>
                      <input
                        id="output-filename"
                        type="text"
                        value={outputFilename}
                        onChange={(e) => setOutputFilename(e.target.value)}
                        placeholder="merged_document.pdf"
                        className="px-2.5 py-1 text-xs rounded-md bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>

                    {/* Merge Action Button */}
                    <div className="w-full sm:w-auto flex items-center justify-end">
                      <Button
                        id="merge-action-btn"
                        onClick={startMerge}
                        disabled={files.length < 2}
                        className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-2 shadow-md shadow-blue-500/20 disabled:opacity-50"
                      >
                        <Layers className="w-4 h-4" />
                        Merge {files.length} Files
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("merge")!} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-xs text-gray-600 dark:text-gray-400">
        <p>DocForge &copy; 2026 &mdash; High Performance PDF Processing.</p>
      </footer>
    </div>
  );
}
