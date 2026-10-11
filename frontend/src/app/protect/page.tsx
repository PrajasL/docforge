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
  Lock,
  Eye,
  EyeOff,
  ShieldCheck,
  KeyRound,
  ShieldAlert,
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
  encryptionAlgorithm?: string;
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

export default function ProtectPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);
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
    const baseName = file.name.replace(/\.pdf$/i, "");
    setOutputFilename(`protected_${baseName}.pdf`);
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
    setConfirmPassword("");
    setErrorMessage(null);
    setStage("idle");
    setResult(null);
    setProgress(0);
    setStatusMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const startProtect = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }

    if (!password.trim()) {
      setErrorMessage("Password cannot be empty.");
      return;
    }

    if (password.length > 128) {
      setErrorMessage("Password cannot exceed 128 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match. Please re-enter your password.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing encryption job...");

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
          tool: "protect",
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
      setStatusMessage("Starting AES-256 encryption engine...");

      // Step 3: Start job with password config
      const finalName = outputFilename.trim() || `protected_${selectedFile.name}`;
      const configPayload: Record<string, any> = {
        password,
        confirm_password: confirmPassword,
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
      setStatusMessage("Encrypting document streams with AES-256...");

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
            setStatusMessage("Finalizing encrypted PDF package...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Document encrypted successfully!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              pageCount: resFile?.page_count,
              isEncrypted: resFile?.is_encrypted ?? true,
              encryptionAlgorithm: resFile?.encryption_algorithm || "AES-256",
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Encryption processing failed on server.");
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
      const msg = err instanceof Error ? err.message : "Unexpected error during encryption.";
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
      setErrorMessage(err.message || "Failed to download protected PDF.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <ToolHeader toolName="Protect PDF" icon={Lock} iconBgColor="bg-rose-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner Info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Protect PDF with Password
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Encrypt your PDF with strong AES-256 encryption. Choose a password that will be required to open and view the file.
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
                ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20 scale-[1.01]"
                : "border-gray-300 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4 shadow-inner">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Upload your PDF file</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-6 max-w-xs">
                Drag and drop your PDF here, or click browse to select a file to encrypt.
              </p>
              <input
                id="protect-file-input"
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                aria-label="Upload PDF file to protect"
                onChange={(e) => e.target.files && handleFileAdded(e.target.files)}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                className="bg-emerald-700 hover:bg-emerald-800 text-white shadow-md shadow-emerald-700/20"
              >
                <FileText className="w-4 h-4 mr-2" />
                Choose PDF File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Config Area (if file selected) */}
        {selectedFile && (
          <div className="space-y-6">
            {/* Selected File Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
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
                  <KeyRound className="w-4 h-4 mr-2 text-emerald-600" />
                  Set Document Password
                </CardTitle>
                <CardDescription className="text-xs">
                  Configure the password required to unlock and open this document.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-5">
                {/* Password Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Password Input */}
                  <div className="space-y-1.5">
                    <label
                      htmlFor="password-input"
                      className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <input
                        id="password-input"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter password..."
                        className="w-full pl-3 pr-10 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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

                  {/* Confirm Password Input */}
                  <div className="space-y-1.5">
                    <label
                      htmlFor="confirm-password-input"
                      className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300"
                    >
                      Confirm Password
                    </label>
                    <div className="relative">
                      <input
                        id="confirm-password-input"
                        type={showConfirmPassword ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Re-enter password..."
                        className="w-full pl-3 pr-10 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                      />
                      <button
                        id="toggle-confirm-password-visibility-btn"
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                        title={showConfirmPassword ? "Hide password" : "Show password"}
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Password Match Status indicator */}
                {password && confirmPassword && (
                  <div className="flex items-center text-xs space-x-1.5">
                    {password === confirmPassword ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                        <span className="text-emerald-700 dark:text-emerald-400 font-medium">
                          Passwords match
                        </span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                        <span className="text-amber-700 dark:text-amber-400 font-medium">
                          Passwords do not match
                        </span>
                      </>
                    )}
                  </div>
                )}

                {/* Output Filename Input */}
                <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
                  <label
                    htmlFor="output-filename-input"
                    className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block"
                  >
                    Output Filename
                  </label>
                  <input
                    id="output-filename-input"
                    type="text"
                    value={outputFilename}
                    onChange={(e) => setOutputFilename(e.target.value)}
                    placeholder="protected_document.pdf"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                {/* Security & DRM Advisory Notice */}
                <div className="p-3.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/60 space-y-2">
                  <div className="flex items-start space-x-2.5">
                    <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-emerald-900 dark:text-emerald-200 leading-relaxed">
                      <p className="font-semibold mb-0.5">Important Security Notice</p>
                      <p>
                        This password will be required every time the document is opened in Adobe Acrobat or any standard PDF reader.
                        We do not log or store passwords on our servers. If you lose this password, the content cannot be recovered.
                      </p>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-emerald-200/50 dark:border-emerald-800/40 text-[11px] text-emerald-700 dark:text-emerald-400 leading-normal">
                    Note: PDF passwords provide strong cryptographic protection (AES-256) for document access, but are not equivalent to centralized DRM systems.
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Action / Progress Area */}
            <div className="pt-2">
              {stage === "idle" && (
                <Button
                  id="start-protect-btn"
                  onClick={startProtect}
                  className="w-full py-6 text-base font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-600/20"
                >
                  <Lock className="w-5 h-5 mr-2" />
                  Protect PDF with Password
                </Button>
              )}

              {(stage === "uploading" || stage === "processing") && (
                <Card className="bg-white dark:bg-gray-900 border-emerald-200 dark:border-emerald-900/60 shadow-md">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <RefreshCw className="w-4 h-4 text-emerald-600 animate-spin" />
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {statusMessage}
                        </span>
                      </div>
                      <span className="text-xs font-bold text-emerald-600">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-emerald-600 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {stage === "completed" && result && (
                <Card className="bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 shadow-sm animate-in fade-in">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-start space-x-3">
                      <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <h4 className="text-base font-bold text-emerald-900 dark:text-emerald-200">
                          PDF Successfully Protected!
                        </h4>
                        <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
                          The document has been encrypted with AES-256 and is ready for download.
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-white/70 dark:bg-gray-900/70 rounded-lg border border-emerald-100 dark:border-emerald-900/50 text-xs">
                      <div>
                        <span className="text-gray-500 block">Total Pages</span>
                        <span className="font-semibold">{result.pageCount ?? "N/A"}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Encryption</span>
                        <span className="font-semibold text-emerald-600">
                          {result.encryptionAlgorithm || "AES-256"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Status</span>
                        <span className="font-semibold text-emerald-700 dark:text-emerald-300">
                          Locked
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Output Size</span>
                        <span className="font-semibold">{formatBytes(result.sizeBytes)}</span>
                      </div>
                    </div>

                    <div className="flex flex-col sm:row gap-3 pt-2">
                      <Button
                        id="download-result-btn"
                        onClick={handleDownload}
                        className="flex-1 py-5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-600/20"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Protected PDF
                      </Button>
                      <Button
                        variant="outline"
                        onClick={clearSelection}
                        className="border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        Protect Another PDF
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("protect")!} />
      </main>
    </div>
  );
}
