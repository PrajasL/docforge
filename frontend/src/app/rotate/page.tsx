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
  RotateCw,
  RotateCcw,
  Compass,
  Layers,
  Sparkles,
  ShieldCheck,
  Check,
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
  rotationAngle?: number;
  rotatedPagesCount?: number;
  totalPageCount?: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type RotationAngle = 90 | 180 | 270;
type RotationScope = "all" | "custom";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function RotatePdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [angle, setAngle] = useState<RotationAngle>(90);
  const [scope, setScope] = useState<RotationScope>("all");
  const [customPages, setCustomPages] = useState<string>("1");
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
    setOutputFilename(`rotated_${file.name}`);
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
    setProgress(0);
    setStatusMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const startRotate = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file to rotate.");
      return;
    }

    if (scope === "custom" && !customPages.trim()) {
      setErrorMessage("Please enter the pages to rotate (e.g. '1, 3' or '2-4').");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing rotation job...");

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
          tool: "rotate",
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
      setStatusMessage("Starting rotation engine...");

      // Step 3: Start job with rotation config
      const finalName = outputFilename.trim() || `rotated_${selectedFile.name}`;
      const configPayload: Record<string, any> = {
        angle,
        pages: scope === "all" ? "all" : customPages.trim(),
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
        throw new Error(errJson?.error?.message || `Failed to start job (${startRes.status})`);
      }

      setStage("processing");
      setStatusMessage("Applying lossless page rotation...");

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
            const currentProgress = job.progress > 50 ? job.progress : 50 + attempts * 4;
            setProgress(Math.min(currentProgress, 95));
            setStatusMessage("Rotating pages and updating document structure...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Rotation completed successfully!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              rotationAngle: resFile?.rotation_angle || angle,
              rotatedPagesCount: resFile?.rotated_pages_count,
              totalPageCount: resFile?.page_count,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Document rotation failed on server.");
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
      const msg = err instanceof Error ? err.message : "Unexpected error during rotation process.";
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
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to download rotated PDF.");
    }
  };

  const getAngleLabel = (deg: number) => {
    switch (deg) {
      case 90:
        return "90° Clockwise";
      case 180:
        return "180° Upside Down";
      case 270:
        return "270° Clockwise (90° CCW)";
      default:
        return `${deg}°`;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <ToolHeader toolName="Rotate PDF" icon={RotateCw} iconBgColor="bg-teal-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Rotate PDF Pages Permanently
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Rotate all pages or specific page ranges by 90°, 180°, or 270°. Fast, clean, and 100% lossless.
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

        {/* If no file is selected, show upload dropzone */}
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
              <div className="w-16 h-16 rounded-2xl bg-teal-50 dark:bg-teal-950/50 text-teal-600 dark:text-teal-400 flex items-center justify-center mb-4 shadow-inner">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Upload your PDF file</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
                Drag and drop your PDF here, or click the button below to browse your local device.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                id="pdf-upload-input"
                aria-label="Upload PDF file to rotate"
                onChange={(e) => {
                  if (e.target.files) handleFileAdded(e.target.files);
                }}
              />
              <Button
                id="select-pdf-button"
                size="lg"
                onClick={() => fileInputRef.current?.click()}
                className="bg-teal-700 hover:bg-teal-800 text-white font-medium shadow-md shadow-teal-700/20"
              >
                Choose PDF File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* If file is selected and not completed, show rotation controls */}
        {selectedFile && stage !== "completed" && (
          <div className="space-y-6">
            {/* Selected File Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardContent className="p-4 sm:p-5 flex items-center justify-between">
                <div className="flex items-center space-x-3 sm:space-x-4 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold truncate text-gray-900 dark:text-gray-100">
                      {selectedFile.name}
                    </h4>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {formatBytes(selectedFile.size)}
                    </p>
                  </div>
                </div>

                {(stage === "idle" || stage === "error") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearSelection}
                    className="text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 p-2"
                    title="Remove file"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Rotation Controls Card */}
            {(stage === "idle" || stage === "error") && (
              <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-bold flex items-center">
                    <Compass className="w-5 h-5 mr-2 text-teal-600" />
                    Rotation Settings
                  </CardTitle>
                  <CardDescription>
                    Choose rotation angle and specify whether to rotate all pages or selected pages.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Angle Options */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Rotation Angle (Clockwise)
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {/* 90 CW */}
                      <button
                        type="button"
                        id="angle-90-btn"
                        onClick={() => setAngle(90)}
                        className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
                          angle === 90
                            ? "border-teal-600 bg-teal-50/60 dark:bg-teal-950/40 text-teal-900 dark:text-teal-100 ring-2 ring-teal-600/30 font-semibold"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-transparent text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        <RotateCw className="w-6 h-6 mb-2 text-teal-600" />
                        <span className="text-sm font-bold">90° Right</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          Quarter turn CW
                        </span>
                      </button>

                      {/* 180 */}
                      <button
                        type="button"
                        id="angle-180-btn"
                        onClick={() => setAngle(180)}
                        className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
                          angle === 180
                            ? "border-teal-600 bg-teal-50/60 dark:bg-teal-950/40 text-teal-900 dark:text-teal-100 ring-2 ring-teal-600/30 font-semibold"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-transparent text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        <RefreshCw className="w-6 h-6 mb-2 text-teal-600" />
                        <span className="text-sm font-bold">180° Flip</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          Upside down
                        </span>
                      </button>

                      {/* 270 CW / 90 CCW */}
                      <button
                        type="button"
                        id="angle-270-btn"
                        onClick={() => setAngle(270)}
                        className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
                          angle === 270
                            ? "border-teal-600 bg-teal-50/60 dark:bg-teal-950/40 text-teal-900 dark:text-teal-100 ring-2 ring-teal-600/30 font-semibold"
                            : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-transparent text-gray-700 dark:text-gray-300"
                        }`}
                      >
                        <RotateCcw className="w-6 h-6 mb-2 text-teal-600" />
                        <span className="text-sm font-bold">270° Left</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          90° CCW / 3/4 turn
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Scope Selection: All vs Custom */}
                  <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-800">
                    <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Pages to Rotate
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        id="scope-all-btn"
                        onClick={() => setScope("all")}
                        className={`p-3 rounded-lg border text-sm font-medium flex items-center justify-center space-x-2 transition-all ${
                          scope === "all"
                            ? "border-teal-600 bg-teal-50 dark:bg-teal-950/50 text-teal-900 dark:text-teal-100 font-semibold"
                            : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                        }`}
                      >
                        <Layers className="w-4 h-4" />
                        <span>All Pages</span>
                      </button>

                      <button
                        type="button"
                        id="scope-custom-btn"
                        onClick={() => setScope("custom")}
                        className={`p-3 rounded-lg border text-sm font-medium flex items-center justify-center space-x-2 transition-all ${
                          scope === "custom"
                            ? "border-teal-600 bg-teal-50 dark:bg-teal-950/50 text-teal-900 dark:text-teal-100 font-semibold"
                            : "border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                        }`}
                      >
                        <Compass className="w-4 h-4" />
                        <span>Specific Pages</span>
                      </button>
                    </div>

                    {scope === "custom" && (
                      <div className="pt-2 space-y-2 animate-in fade-in duration-150">
                        <label
                          htmlFor="custom-pages-input"
                          className="block text-xs font-medium text-gray-700 dark:text-gray-300"
                        >
                          Page numbers or ranges (1-indexed)
                        </label>
                        <input
                          id="custom-pages-input"
                          type="text"
                          value={customPages}
                          onChange={(e) => setCustomPages(e.target.value)}
                          placeholder="e.g. 1, 3, 5-7"
                          className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        />
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Examples: <code className="text-teal-600 dark:text-teal-400">1</code>,{" "}
                          <code className="text-teal-600 dark:text-teal-400">1, 3, 5</code>, or{" "}
                          <code className="text-teal-600 dark:text-teal-400">2-4</code>.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Output Filename */}
                  <div className="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                    <label
                      htmlFor="output-filename-input"
                      className="block text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
                    >
                      Output Filename (Optional)
                    </label>
                    <input
                      id="output-filename-input"
                      type="text"
                      value={outputFilename}
                      onChange={(e) => setOutputFilename(e.target.value)}
                      placeholder={`rotated_${selectedFile.name}`}
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                  </div>

                  {/* Action button */}
                  <div className="pt-4 flex justify-end">
                    <Button
                      id="start-rotate-btn"
                      size="lg"
                      onClick={startRotate}
                      className="w-full sm:w-auto bg-teal-600 hover:bg-teal-700 text-white font-semibold px-8 shadow-md shadow-teal-600/20"
                    >
                      <RotateCw className="w-4 h-4 mr-2" />
                      Rotate PDF Now
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Progress Card */}
            {(stage === "uploading" || stage === "processing") && (
              <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm p-6 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-teal-50 dark:bg-teal-950/60 text-teal-600 flex items-center justify-center mx-auto animate-spin">
                  <RefreshCw className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {stage === "uploading" ? "Uploading Document" : "Rotating Pages"}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{statusMessage}</p>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-teal-600 h-2.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="text-xs text-gray-400">{progress}% complete</div>
              </Card>
            )}
          </div>
        )}

        {/* Completion Result Card */}
        {stage === "completed" && result && (
          <Card className="bg-white dark:bg-gray-900 border-teal-200 dark:border-teal-900/60 shadow-md overflow-hidden animate-in fade-in duration-200">
            <div className="bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-teal-500/10 p-6 sm:p-8 text-center border-b border-teal-100 dark:border-teal-900/40">
              <div className="w-16 h-16 rounded-2xl bg-teal-600 text-white flex items-center justify-center mx-auto mb-4 shadow-lg shadow-teal-600/30">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Rotation Complete!
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Your PDF has been rotated losslessly and is ready for download.
              </p>
            </div>

            <CardContent className="p-6 sm:p-8 space-y-6">
              {/* Summary Stats Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">
                    Rotation Applied
                  </span>
                  <span className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {getAngleLabel(result.rotationAngle || angle)}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">
                    Pages Rotated
                  </span>
                  <span className="text-base font-bold text-teal-600 dark:text-teal-400">
                    {result.rotatedPagesCount !== undefined
                      ? `${result.rotatedPagesCount} page(s)`
                      : scope === "all"
                      ? "All pages"
                      : "Selected"}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-center">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">
                    Result File Size
                  </span>
                  <span className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {formatBytes(result.sizeBytes)}
                  </span>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Button
                  id="download-result-btn"
                  size="lg"
                  onClick={handleDownload}
                  className="flex-1 bg-teal-600 hover:bg-teal-700 text-white font-bold py-6 shadow-md shadow-teal-600/20"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Download Rotated PDF
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={clearSelection}
                  className="py-6 border-gray-300 dark:border-gray-700"
                >
                  Rotate Another PDF
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Feature Highlights / Info Box */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6">
          <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 flex items-start space-x-3">
            <Sparkles className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold">100% Lossless</h5>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Rotation modifies document view metadata without re-encoding fonts, images, or vectors.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 flex items-start space-x-3">
            <Layers className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold">Flexible Scope</h5>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Rotate all pages simultaneously or selectively specify individual page numbers and ranges.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 flex items-start space-x-3">
            <ShieldCheck className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold">Auto-Purged</h5>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Uploaded and rotated files are automatically cleaned up after 2 hours from isolated storage.
              </p>

            </div>
          </div>
        </div>

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("rotate")!} />
      </main>
    </div>
  );
}
