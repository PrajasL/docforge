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
  Unlock,
  Eye,
  EyeOff,
  KeyRound,
  ShieldAlert,
  ShieldCheck,
  LockOpen,
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
  isEncrypted?: boolean;
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

export default function UnlockPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [password, setPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
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
    setSelectedFile({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
    });
    const baseName = file.name.replace(/\.pdf$/i, "").replace(/^protected_/i, "");
    setOutputFilename(`unlocked_${baseName}.pdf`);
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
    setPassword("");
    setErrorMessage(null);
    setStage("idle");
    setResult(null);
    setProgress(0);
    setStatusMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const startUnlock = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a password-protected PDF file first.");
      return;
    }

    if (!password.trim()) {
      setErrorMessage("Password is required to unlock this PDF.");
      return;
    }

    if (password.length > 128) {
      setErrorMessage("Password cannot exceed 128 characters.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing unlock job...");

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
          tool: "unlock",
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
      setStatusMessage("Validating security credentials...");

      // Step 3: Start job with ephemeral password
      const finalName = outputFilename.trim() || `unlocked_${selectedFile.name}`;
      const configPayload: Record<string, any> = {
        password,
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
        throw new Error(errJson?.error?.message || `Failed to start unlock job (${startRes.status})`);
      }

      setStage("processing");
      setStatusMessage("Decrypting PDF streams and removing security restrictions...");

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
            setStatusMessage("Removing encryption and generating unrestricted document...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Document unlocked successfully!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              pageCount: resFile?.page_count,
              isEncrypted: resFile?.is_encrypted ?? false,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Decryption failed on server. Please check the password.");
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
      const msg = err instanceof Error ? err.message : "Unexpected error during unlock operation.";
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
      const msg = err instanceof Error ? err.message : "Failed to download unlocked file.";
      setErrorMessage(msg);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Unlock PDF" icon={Unlock} iconBgColor="bg-cyan-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner Info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Unlock Password-Protected PDF
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Remove password security from your PDF file so it can be viewed and shared freely without prompting for a password.
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
                Choose a password-protected PDF to unlock
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
                Drag and drop your protected PDF here, or browse files from your computer.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                id="pdf-upload-input"
                aria-label="Upload PDF file to unlock"
                onChange={(e) => {
                  if (e.target.files) handleFileAdded(e.target.files);
                }}
              />
              <Button
                id="select-file-btn"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="bg-amber-500 hover:bg-amber-600 text-stone-950 font-semibold shadow-sm"
              >
                Select Protected PDF
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
                  <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="truncate">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {formatBytes(selectedFile.size)}
                    </p>
                  </div>
                </div>
                {stage !== "uploading" && stage !== "processing" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearSelection}
                    className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                    title="Remove file"
                  >
                    <Trash2 className="w-4 h-4 mr-1.5" />
                    Change File
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Password Configuration Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardHeader className="pb-4 border-b border-gray-100 dark:border-gray-800">
                <CardTitle className="text-base font-semibold flex items-center">
                  <KeyRound className="w-4 h-4 mr-2 text-amber-600" />
                  Enter Document Password
                </CardTitle>
                <CardDescription className="text-xs">
                  Supply the current password for this document to decrypt and remove protection.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-5">
                {/* Password Input */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="password-input"
                    className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300"
                  >
                    Document Password
                  </label>
                  <div className="relative">
                    <input
                      id="password-input"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter the existing password..."
                      disabled={stage === "uploading" || stage === "processing" || stage === "completed"}
                      className="w-full pl-3 pr-10 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-amber-500 focus:outline-none disabled:opacity-50"
                    />
                    <button
                      id="toggle-password-visibility-btn"
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                      title={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

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
                    placeholder="unlocked_document.pdf"
                    disabled={stage === "uploading" || stage === "processing" || stage === "completed"}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-amber-500 focus:outline-none disabled:opacity-50"
                  />
                </div>

                {/* Security Note Callout */}
                <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200/70 dark:border-amber-800/60 text-xs text-amber-800 dark:text-amber-300 space-y-1">
                  <div className="font-semibold flex items-center">
                    <ShieldAlert className="w-3.5 h-3.5 mr-1.5 flex-shrink-0 text-amber-600" />
                    Authorized Decryption Only
                  </div>
                  <p className="text-amber-700/90 dark:text-amber-300/80 leading-relaxed">
                    DocForge verifies the exact password you supply and produces an unencrypted copy. It does not attempt password recovery, brute-forcing, or bypassing unknown passwords.
                  </p>
                </div>

                {/* Action Trigger Button */}
                {stage !== "completed" && (
                  <Button
                    id="unlock-submit-btn"
                    onClick={startUnlock}
                    disabled={stage === "uploading" || stage === "processing" || !password.trim()}
                    className="w-full bg-amber-600 hover:bg-amber-700 text-white shadow-sm flex items-center justify-center space-x-2 py-2.5 font-medium"
                  >
                    {stage === "uploading" || stage === "processing" ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                        <span>Processing Unlock...</span>
                      </>
                    ) : (
                      <>
                        <Unlock className="w-4 h-4 mr-2" />
                        <span>Unlock PDF</span>
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
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin text-amber-600" />
                      {statusMessage}
                    </span>
                    <span className="text-amber-600 font-semibold">{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-amber-600 h-full transition-all duration-300 rounded-full"
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
                      PDF Successfully Unlocked!
                    </CardTitle>
                  </div>
                  <CardDescription className="text-xs text-emerald-800/80 dark:text-emerald-300/80">
                    All password protection has been completely removed. Your document can now be opened without entering a password.
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
                        Pages
                      </span>
                      <span className="text-sm font-semibold block mt-0.5">
                        {result.pageCount ?? "Unknown"} Pages
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500 uppercase tracking-wider block">
                        Security Status
                      </span>
                      <span className="inline-flex items-center mt-0.5 px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        <LockOpen className="w-3 h-3 mr-1" />
                        Unrestricted
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3 pt-2">
                    <Button
                      id="download-result-btn"
                      onClick={handleDownload}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm flex items-center justify-center space-x-2 py-2.5 font-medium"
                    >
                      <Download className="w-4 h-4 mr-1.5" />
                      <span>Download Unlocked PDF</span>
                    </Button>
                    <Button
                      id="unlock-another-btn"
                      variant="outline"
                      onClick={clearSelection}
                      className="border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <RefreshCw className="w-4 h-4 mr-1.5" />
                      Unlock Another PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("unlock")!} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-600 dark:text-gray-400">
        DocForge PDF Platform &bull; Phase 2 PDF Tools &bull; Safe &amp; Ephemeral Memory Execution
      </footer>
    </div>
  );
}
