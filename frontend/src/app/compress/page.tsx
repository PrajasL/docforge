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
  Minimize2,
  Info,
  Check,
  ShieldCheck,
  Zap,
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
  originalSizeBytes: number;
  savingsBytes: number;
  savingsPercentage: number;
  isAlreadyOptimal: boolean;
  compressionLevel: string;
  pageCount?: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type CompressionLevel = "recommended" | "balanced" | "maximum";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function CompressPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [level, setLevel] = useState<CompressionLevel>("recommended");
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
    setOutputFilename(`compressed_${file.name}`);
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

  const startCompress = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file to compress.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing compression job...");

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
          tool: "compress",
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
      setStatusMessage("Uploading document to secure storage...");

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
      setStatusMessage("Starting optimization engine...");

      // Step 3: Start job with compression level
      const finalName = outputFilename.trim() || `compressed_${selectedFile.name}`;
      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: {
            level,
            output_filename: finalName,
          },
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to start job (${startRes.status})`);
      }

      setStage("processing");
      setStatusMessage("Optimizing streams, fonts, and images...");

      // Step 4: Poll job status until COMPLETED or FAILED
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
            const currentProgress = job.progress > 50 ? job.progress : 50 + attempts * 3;
            setProgress(Math.min(currentProgress, 95));
            setStatusMessage("Applying stream and image compression...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Compression completed!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              originalSizeBytes: resFile?.original_size_bytes || selectedFile.size,
              savingsBytes: resFile?.savings_bytes || 0,
              savingsPercentage: resFile?.savings_percentage || 0,
              isAlreadyOptimal: !!resFile?.is_already_optimal,
              compressionLevel: resFile?.compression_level || level,
              pageCount: resFile?.page_count,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Compression failed during processing.");
          }

          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage("Operation timed out. Please try again.");
          }
        } catch (pollErr: any) {
          clearInterval(pollInterval);
          setStage("error");
          setErrorMessage(pollErr.message || "Failed polling job status.");
        }
      }, 800);
    } catch (err: any) {
      setStage("error");
      setErrorMessage(err.message || "An unexpected error occurred during compression.");
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
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to download compressed PDF.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Compress PDF" icon={Minimize2} iconBgColor="bg-emerald-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Page Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            Compress PDF Document
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm sm:text-base">
            Optimize content streams and embedded images to shrink file size while preserving readability and document structure.
          </p>
        </div>

        {/* Global Error Banner */}
        {errorMessage && (
          <div
            id="global-error-banner"
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
          <Card className="border-emerald-300 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-md">
            <CardContent className="pt-8 pb-8 text-center space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <div className="space-y-1">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  PDF Successfully Compressed!
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {result.isAlreadyOptimal
                    ? "Your document is already optimally compressed. The original quality has been fully preserved."
                    : `Saved ${formatBytes(result.savingsBytes)} (${result.savingsPercentage}% reduction) without losing document structure.`}
                </p>
              </div>

              {/* Stats Comparison Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto">
                <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                  <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                    Original Size
                  </span>
                  <span className="text-base font-bold text-gray-800 dark:text-gray-200 mt-1 block">
                    {formatBytes(result.originalSizeBytes)}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                  <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                    Compressed Size
                  </span>
                  <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1 block">
                    {formatBytes(result.sizeBytes)}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                  <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider block">
                    Total Savings
                  </span>
                  <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1 block">
                    {result.isAlreadyOptimal ? "0% (Optimal)" : `-${result.savingsPercentage}%`}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button
                  id="download-compressed-pdf-btn"
                  onClick={handleDownload}
                  size="lg"
                  className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-2 shadow-lg shadow-emerald-600/20"
                >
                  <Download className="w-5 h-5" />
                  Download Compressed PDF
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={clearSelection}
                  className="w-full sm:w-auto"
                >
                  Compress Another PDF
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PROCESSING & UPLOADING PROGRESS STATE */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-emerald-200 dark:border-emerald-900/50 shadow-md">
            <CardContent className="py-10 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto animate-pulse">
                <RefreshCw className="w-7 h-7 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  {stage === "uploading" ? "Uploading Document" : "Compressing PDF"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{statusMessage}</p>
              </div>

              {/* Progress Bar */}
              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-emerald-600 h-3 rounded-full transition-all duration-300 ease-out"
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
                    ? "border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/30 scale-[1.01]"
                    : "border-gray-300 dark:border-gray-800 hover:border-emerald-400 hover:bg-gray-50/50 dark:hover:bg-gray-900/40"
                }`}
              >
                <input
                  id="compress-file-input"
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  aria-label="Upload PDF file to compress"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileAdded(e.target.files);
                      e.target.value = "";
                    }
                  }}
                />

                <div className="flex flex-col items-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shadow-inner">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-base font-semibold text-gray-800 dark:text-gray-200">
                      Choose a PDF file or drag & drop it here
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Select 1 PDF file to compress and optimize.
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
              <Card className="shadow-sm border-emerald-200/60 dark:border-emerald-900/40">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <FileText className="w-4 h-4 text-emerald-600" /> Selected Document
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Ready for compression. Select your desired compression tier below.
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

                <CardContent className="space-y-5 pt-1">
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

                  {/* Compression Options (3 Tiers) */}
                  <div className="space-y-3">
                    <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block">
                      Compression Tier
                    </label>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {/* Tier 1: Recommended */}
                      <button
                        type="button"
                        onClick={() => setLevel("recommended")}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                          level === "recommended"
                            ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-600 text-emerald-950 dark:text-emerald-100"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
                        }`}
                      >
                        <div>
                          <div className="font-semibold text-sm flex items-center justify-between">
                            <span>Recommended</span>
                            {level === "recommended" && <Check className="w-4 h-4 text-emerald-600" />}
                          </div>
                          <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300 mt-0.5">
                            Standard Compression
                          </p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-2">
                            Optimal balance of file size and visual fidelity. Best for business documents and reports.
                          </p>
                        </div>
                        <div className="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800/60 text-[10px] text-gray-400">
                          Negligible image quality impact
                        </div>
                      </button>

                      {/* Tier 2: Balanced */}
                      <button
                        type="button"
                        onClick={() => setLevel("balanced")}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                          level === "balanced"
                            ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-600 text-emerald-950 dark:text-emerald-100"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
                        }`}
                      >
                        <div>
                          <div className="font-semibold text-sm flex items-center justify-between">
                            <span>Balanced</span>
                            {level === "balanced" && <Check className="w-4 h-4 text-emerald-600" />}
                          </div>
                          <p className="text-xs font-medium text-blue-700 dark:text-blue-300 mt-0.5">
                            Strong Compression
                          </p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-2">
                            Noticeable file size reduction with moderate downsampling. Perfect for web sharing.
                          </p>
                        </div>
                        <div className="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800/60 text-[10px] text-gray-400">
                          Minor image quality impact
                        </div>
                      </button>

                      {/* Tier 3: Maximum */}
                      <button
                        type="button"
                        onClick={() => setLevel("maximum")}
                        className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                          level === "maximum"
                            ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-600 text-emerald-950 dark:text-emerald-100"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
                        }`}
                      >
                        <div>
                          <div className="font-semibold text-sm flex items-center justify-between">
                            <span>Maximum</span>
                            {level === "maximum" && <Check className="w-4 h-4 text-emerald-600" />}
                          </div>
                          <p className="text-xs font-medium text-purple-700 dark:text-purple-300 mt-0.5">
                            Extreme Compression
                          </p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-2">
                            Maximum reduction for strict upload or email limits. Applies aggressive compression.
                          </p>
                        </div>
                        <div className="mt-3 pt-2 border-t border-gray-100 dark:border-gray-800/60 text-[10px] text-gray-400">
                          Quality reduced on large photos
                        </div>
                      </button>
                    </div>

                    {/* Explanatory Callout */}
                    <div className="p-3 rounded-lg bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/60 dark:border-blue-900/40 text-blue-900 dark:text-blue-200 text-xs flex items-start space-x-2.5">
                      <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <p className="font-medium">Compression Notice</p>
                        <p className="text-blue-700 dark:text-blue-300">
                          Stronger compression reduces image resolution and applies lossy JPEG encoding. Text, vector lines, page dimensions, and readable contents are fully preserved.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Output Filename & Action */}
                  <div className="pt-3 border-t border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="w-full sm:w-auto flex items-center space-x-2 text-xs">
                      <label htmlFor="output-filename" className="text-gray-500 font-medium">
                        Output Name:
                      </label>
                      <input
                        id="output-filename"
                        type="text"
                        value={outputFilename}
                        onChange={(e) => setOutputFilename(e.target.value)}
                        placeholder={`compressed_${selectedFile.name}`}
                        className="px-2.5 py-1 text-xs rounded-md bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>

                    {/* Compress Action Button */}
                    <div className="w-full sm:w-auto flex items-center justify-end">
                      <Button
                        id="compress-action-btn"
                        onClick={startCompress}
                        className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-2 shadow-md shadow-emerald-500/20"
                      >
                        <Minimize2 className="w-4 h-4" />
                        Compress PDF
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("compress")!} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-xs text-gray-600 dark:text-gray-400 mt-auto">
        <p>DocForge &copy; 2026 &mdash; Modular Monolith PDF Processing Engine.</p>
        <p className="mt-1">Compress PDF &bull; Stream Optimization &bull; Clean Room Architecture</p>
      </footer>
    </div>
  );
}
