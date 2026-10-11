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
  Image as ImageIcon,
  Info,
  Check,
  Layers,
  Sparkles,
  Sliders,
  ShieldCheck,
  Archive,
} from "lucide-react";
import { countPdfPages } from "@/app/extract-pages/page";
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
  pageCount: number;
  fileCount: number;
  dpi: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type ResolutionOption = 150 | 300;

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function PdfToJpgPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [dpi, setDpi] = useState<ResolutionOption>(150);
  const [quality, setQuality] = useState<number>(85);
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

    if (file.size === 0) {
      setErrorMessage(`File '${file.name}' is empty (0 bytes).`);
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage(`File '${file.name}' (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds maximum allowed size of 50 MB.`);
      return;
    }

    setErrorMessage(null);
    const baseName = file.name.replace(/\.pdf$/i, "");
    setOutputFilename(`${baseName}_images.zip`);

    setSelectedFile({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      detectedPages: null,
    });

    // Detect page count asynchronously
    countPdfPages(file).then((detected) => {
      if (detected !== null) {
        setSelectedFile((prev) => (prev && prev.name === file.name ? { ...prev, detectedPages: detected } : prev));
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

  const startConversion = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }

    if (typeof selectedFile.detectedPages === "number") {
      if (dpi > 150 && selectedFile.detectedPages > 50) {
        setErrorMessage(
          `This document has ${selectedFile.detectedPages} pages. High-resolution (300 DPI) conversion is limited to 50 pages. Please select Standard (150 DPI) or split your PDF.`
        );
        return;
      }
      if (selectedFile.detectedPages > 100) {
        setErrorMessage(
          `This document has ${selectedFile.detectedPages} pages. Maximum supported document length is 100 pages. Please split your PDF first.`
        );
        return;
      }
    }

    setStage("uploading");
    setProgress(5);
    setStatusMessage("Preparing document for conversion...");
    setErrorMessage(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const sessionId = sessionIdRef.current;
    const finalName = outputFilename.trim() || `${selectedFile.name.replace(/\.pdf$/i, "")}_images.zip`;

    try {
      // Step 1: Create job
      const createRes = await fetch(`${apiUrl}/api/v1/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          tool: "pdf_to_jpg",
          files: [
            {
              name: selectedFile.name,
              size: selectedFile.size,
              content_type: "application/pdf",
            },
          ],
          config: {
            dpi,
            quality,
            output_filename: finalName,
          },
        }),
      });

      if (!createRes.ok) {
        const errJson = await createRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to create job (${createRes.status})`);
      }

      const createData = await createRes.json();
      const jobId = createData.data.job.id;
      const uploadItem = createData.data.uploads[0];

      setProgress(20);
      setStatusMessage("Uploading PDF to processing server...");

      // Step 2: Upload file (direct PUT)
      let uploadSuccess = false;
      try {
        const uploadRes = await fetch(uploadItem.upload_url, {
          method: "PUT",
          headers: {
            "Content-Type": "application/pdf",
          },
          body: selectedFile.file,
        });
        if (uploadRes.ok) uploadSuccess = true;
      } catch {
        uploadSuccess = false;
      }

      if (!uploadSuccess) {
        const directRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/files/${uploadItem.file_id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/pdf",
            "X-Session-Id": sessionId,
          },
          body: selectedFile.file,
        });
        if (!directRes.ok) {
          throw new Error(`Failed to upload file to server (${directRes.status})`);
        }
      }

      // Step 3: Confirm upload & start job
      setProgress(40);
      setStatusMessage("Registering file with Celery worker...");

      await fetch(`${apiUrl}/api/v1/jobs/${jobId}/files/${uploadItem.file_id}/confirm`, {
        method: "POST",
        headers: {
          "X-Session-Id": sessionId,
        },
      }).catch(() => {});

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: {
            dpi,
            quality,
            output_filename: finalName,
          },
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || `Failed to start job (${startRes.status})`);
      }

      setStage("processing");
      setStatusMessage("Rendering pages and encoding JPG images...");

      // Step 4: Poll job progress
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
            const currentProgress = job.progress > 40 ? job.progress : 40 + attempts * 3;
            setProgress(Math.min(currentProgress, 95));
            setStatusMessage("Converting pages to high-resolution JPEG images...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Conversion complete!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              pageCount: resFile?.page_count || selectedFile.detectedPages || 1,
              fileCount: resFile?.file_count || resFile?.page_count || 1,
              dpi: resFile?.dpi || dpi,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Conversion failed during processing.");
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
      setErrorMessage(err.message || "An unexpected error occurred during conversion.");
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
      setErrorMessage(err.message || "Failed to download converted images.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="PDF to JPG" icon={ImageIcon} iconBgColor="bg-orange-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner Info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Convert PDF to JPG Images
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Turn every page of your PDF into an individual, high-quality JPG image and download them bundled in a ZIP archive.
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
                ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/20 scale-[1.01]"
                : "border-gray-300 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="w-16 h-16 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                Choose a PDF to convert to JPG
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
                aria-label="Upload PDF file to convert to JPG"
                onChange={(e) => {
                  if (e.target.files) handleFileAdded(e.target.files);
                }}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                className="bg-amber-500 hover:bg-amber-600 text-stone-950 font-semibold shadow-md shadow-amber-500/20 px-6 py-2"
              >
                Select PDF File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Selected File & Settings */}
        {selectedFile && (
          <div className="space-y-6">
            {/* File Info Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0">
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
                          className="inline-flex items-center px-2 py-0.5 rounded-full font-medium bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200/50"
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

            {/* Conversion Settings Card */}
            {stage !== "completed" && (
              <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
                <CardHeader className="pb-4 border-b border-gray-100 dark:border-gray-800">
                  <CardTitle className="text-base font-semibold flex items-center">
                    <Sliders className="w-4 h-4 mr-2 text-amber-600" />
                    Image Quality &amp; Resolution
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Choose resolution and options for the generated JPEG images.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  {/* Resolution Toggle */}
                  <div className="space-y-3">
                    <label className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Rendering Resolution
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Standard 150 DPI */}
                      <div
                        onClick={() => setDpi(150)}
                        id="dpi-150-card"
                        className={`cursor-pointer rounded-xl p-4 border transition-all ${
                          dpi === 150
                            ? "border-amber-600 bg-amber-50/40 dark:bg-amber-950/20 ring-2 ring-amber-500/20 shadow-sm"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="font-semibold text-sm">Standard (150 DPI)</h4>
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                Recommended
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Fast conversion, optimal for web, screens, and presentations (up to 100 pages).
                            </p>
                          </div>
                          {dpi === 150 && <Check className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />}
                        </div>
                      </div>

                      {/* High 300 DPI */}
                      <div
                        onClick={() => setDpi(300)}
                        id="dpi-300-card"
                        className={`cursor-pointer rounded-xl p-4 border transition-all ${
                          dpi === 300
                            ? "border-amber-600 bg-amber-50/40 dark:bg-amber-950/20 ring-2 ring-amber-500/20 shadow-sm"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="font-semibold text-sm">High Resolution (300 DPI)</h4>
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300">
                                Print Ready
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              Ultra crisp detail, ideal for printing and high-DPI displays (up to 50 pages).
                            </p>
                          </div>
                          {dpi === 300 && <Check className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Quality Selector */}
                  <div className="space-y-3 pt-2">
                    <label className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider flex items-center justify-between">
                      <span>JPEG Encoding Quality</span>
                      <span className="text-amber-600 dark:text-amber-400 font-mono text-xs">{quality}%</span>
                    </label>
                    <div className="flex items-center space-x-4">
                      <button
                        type="button"
                        onClick={() => setQuality(85)}
                        id="quality-85-btn"
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                          quality === 85
                            ? "bg-amber-50 border-amber-600 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                            : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                        }`}
                      >
                        85% (Balanced)
                      </button>
                      <button
                        type="button"
                        onClick={() => setQuality(95)}
                        id="quality-95-btn"
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                          quality === 95
                            ? "bg-amber-50 border-amber-600 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                            : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                        }`}
                      >
                        95% (Maximum)
                      </button>
                    </div>
                  </div>

                  {/* Custom Output Filename */}
                  <div className="space-y-2 pt-2">
                    <label className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider block">
                      Custom Output ZIP Filename
                    </label>
                    <input
                      type="text"
                      id="output-filename-input"
                      value={outputFilename}
                      onChange={(e) => setOutputFilename(e.target.value)}
                      placeholder="converted_images.zip"
                      className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                    <p className="text-[11px] text-gray-400">
                      Converted JPGs will be named page_01.jpg, page_02.jpg, etc., inside this archive.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action Button & Progress */}
            {stage !== "completed" && (
              <div className="space-y-4">
                {(stage === "uploading" || stage === "processing") && (
                  <div className="p-5 rounded-xl border border-amber-100 dark:border-amber-900/50 bg-white dark:bg-gray-900 space-y-3 shadow-sm">
                    <div className="flex items-center justify-between text-xs font-semibold text-gray-600 dark:text-gray-300">
                      <span className="flex items-center space-x-2">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
                        <span>{statusMessage}</span>
                      </span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-amber-600 to-orange-600 h-full transition-all duration-300 ease-out"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}

                <Button
                  id="pdf-to-jpg-submit-btn"
                  onClick={startConversion}
                  disabled={stage === "uploading" || stage === "processing"}
                  className="w-full bg-gradient-to-r from-amber-600 via-orange-600 to-red-600 hover:from-amber-700 hover:to-red-700 text-white font-bold py-3 text-base shadow-lg hover:shadow-xl transition-all"
                >
                  {stage === "uploading" || stage === "processing" ? (
                    <span className="flex items-center space-x-2">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Converting PDF to JPG...</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-2">
                      <ImageIcon className="w-4 h-4" />
                      <span>Convert All Pages to JPG</span>
                    </span>
                  )}
                </Button>
              </div>
            )}

            {/* Completed Result Card */}
            {stage === "completed" && result && (
              <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm animate-in fade-in zoom-in-95 duration-200">
                <CardHeader className="text-center pb-4 border-b border-gray-100 dark:border-gray-800">
                  <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-950/60 text-green-600 flex items-center justify-center mx-auto mb-2">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <CardTitle className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Conversion Successful!
                  </CardTitle>
                  <CardDescription className="text-xs">
                    All pages have been converted to JPG images and packaged into a ZIP archive.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  {/* Result Stats */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                      <span className="text-[11px] font-medium text-gray-500 block uppercase">Pages Converted</span>
                      <span className="text-lg font-bold text-amber-600 dark:text-amber-400">
                        {result.pageCount} Pages
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                      <span className="text-[11px] font-medium text-gray-500 block uppercase">Resolution</span>
                      <span className="text-lg font-bold text-gray-800 dark:text-gray-200">
                        {result.dpi} DPI
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                      <span className="text-[11px] font-medium text-gray-500 block uppercase">Archive Size</span>
                      <span className="text-lg font-bold text-gray-800 dark:text-gray-200">
                        {formatBytes(result.sizeBytes)}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="space-y-3">
                    <Button
                      id="download-result-btn"
                      onClick={handleDownload}
                      className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-3 text-base shadow-lg hover:shadow-xl transition-all"
                    >
                      <Download className="w-5 h-5 mr-2" />
                      Download ZIP Archive ({formatBytes(result.sizeBytes)})
                    </Button>
                    <Button
                      variant="outline"
                      onClick={clearSelection}
                      className="w-full text-xs text-gray-600 dark:text-gray-400"
                    >
                      Convert Another PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Feature Highlights & Privacy Card */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 flex flex-col items-center text-center space-y-2">
            <Archive className="w-5 h-5 text-amber-600" />
            <h4 className="font-semibold text-xs">Bundled ZIP Archive</h4>
            <p className="text-[11px] text-gray-600 dark:text-gray-400">
              Download every converted page organized into a single, clean ZIP folder.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 flex flex-col items-center text-center space-y-2">
            <Sparkles className="w-5 h-5 text-orange-600" />
            <h4 className="font-semibold text-xs">Print &amp; Web Resolutions</h4>
            <p className="text-[11px] text-gray-600 dark:text-gray-400">
              Choose 150 DPI for web and email or 300 DPI for high-definition print rendering.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 flex flex-col items-center text-center space-y-2">
            <ShieldCheck className="w-5 h-5 text-green-600" />
            <h4 className="font-semibold text-xs">100% Private &amp; Secure</h4>
            <p className="text-[11px] text-gray-600 dark:text-gray-400">
              Processed privately in our backend engine; never sent to third-party APIs.
            </p>
          </div>
        </div>

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("pdf-to-jpg")!} />
      </main>
    </div>
  );
}
