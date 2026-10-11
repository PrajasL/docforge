"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ToolHeader } from "@/components/tool-header";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Download,
  RefreshCw,
  Wrench,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Info,
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
  repaired?: boolean;
  repairAction?: string;
  statusDetail?: string;
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

export default function RepairPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
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
    const baseName = file.name.replace(/\.[^/.]+$/, "");
    setOutputFilename(`repaired_${baseName}.pdf`);
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
    setOutputFilename("");
  };

  const startRepair = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file to repair.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Creating repair job...");

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
          tool: "repair",
          files: [
            {
              name: selectedFile.name,
              size: selectedFile.size,
              content_type: selectedFile.file.type || "application/pdf",
            },
          ],
          config: {
            output_filename: outputFilename.trim() || `repaired_${selectedFile.name}`,
          },
        }),
      });

      if (!createRes.ok) {
        const errJson = await createRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || "Failed to create repair job.");
      }

      const createData = await createRes.json();
      const jobId = createData.data.job.id;
      const uploadInfo = createData.data.uploads[0];

      // Step 2: Upload file bytes directly via API endpoint
      setStatusMessage("Uploading document to private worker storage...");
      setProgress(25);

      const uploadRes = await fetch(
        `${apiUrl}/api/v1/jobs/${jobId}/files/${uploadInfo.file_id}`,
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
        throw new Error(errJson?.error?.message || `Failed to upload document (${uploadRes.status})`);
      }

      // Step 3: Start repair job
      setStage("processing");
      setStatusMessage("Scanning document structure & cross-reference tables...");
      setProgress(45);

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          config: {
            output_filename: outputFilename.trim() || `repaired_${selectedFile.name}`,
          },
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || "Failed to start repair job.");
      }

      // Step 4: Poll status
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
          const workerProgress = Math.max(45, Math.min(95, job.progress));
          setProgress(workerProgress);
          setStatusMessage("Reconstructing tables & salvaging pages...");
        } else if (job.status === "COMPLETED") {
          isDone = true;
          setProgress(100);
          setStage("completed");
          setResult({
            jobId: job.id,
            filename: job.result_file?.original_name || `repaired_${selectedFile.name}`,
            sizeBytes: job.result_file?.size_bytes || 0,
            pageCount: job.result_file?.page_count,
            repaired: job.result_file?.repaired,
            repairAction: job.result_file?.repair_action,
            statusDetail: job.result_file?.status_detail,
          });
          setStatusMessage("Document repair complete!");
          return;
        } else if (job.status === "FAILED") {
          const code = job.error_code;
          let msg = job.error_message || "Document repair failed in worker.";
          if (code === "PDF_ENCRYPTED") {
            msg = `File '${selectedFile.name}' is password-protected. Please unlock it using the Unlock PDF tool before repairing.`;
          } else if (code === "UNRECOVERABLE_PDF") {
            msg = `File '${selectedFile.name}' is severely corrupted and could not be structurally recovered.`;
          }
          throw new Error(msg);
        }
      }

      if (!isDone) {
        throw new Error("Repair processing timed out. Please try again.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred during repair.";
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

  const seoData = getToolSeoData("repair-pdf");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Repair PDF" icon={Wrench} iconBgColor="bg-amber-600" />

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            Repair Corrupted PDF Document
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Safely reconstruct damaged cross-reference tables, trailers, and corrupted object streams. Recovered pages are compiled into a newly generated document without modifying your original upload.
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
              <p className="font-medium">Repair Error</p>
              <p className="text-red-700 dark:text-red-300 mt-0.5">{errorMessage}</p>
            </div>
            <button
              type="button"
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
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {result.repaired ? "PDF Successfully Repaired!" : "Document Structure Verified!"}
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-300 max-w-lg mx-auto">
                  {result.statusDetail ||
                    (result.repaired
                      ? "Damaged structural elements were successfully recovered into a fresh document."
                      : "Document was already structurally sound. A standardized, normalized copy has been generated.")}
                </p>
              </div>

              {/* Status Badge */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                {result.repaired ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-emerald-700 dark:text-emerald-400">Structural Damage Repaired</span>
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-blue-500" />
                    <span className="text-blue-700 dark:text-blue-400">Structurally Sound (Verified)</span>
                  </>
                )}
              </div>

              {/* Result Meta Details */}
              <div className="inline-flex items-center gap-4 px-4 py-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-300">
                <span className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-amber-600" />
                  {result.filename}
                </span>
                <span>&bull;</span>
                <span>{formatBytes(result.sizeBytes)}</span>
                {result.pageCount !== undefined && (
                  <>
                    <span>&bull;</span>
                    <span>{result.pageCount} page(s) recovered</span>
                  </>
                )}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button
                  id="download-repaired-pdf-btn"
                  onClick={handleDownload}
                  size="lg"
                  className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold gap-2 shadow-lg shadow-green-600/20"
                >
                  <Download className="w-5 h-5" />
                  Download Repaired PDF
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={clearSelection}
                  className="w-full sm:w-auto"
                >
                  Repair Another Document
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PROCESSING & UPLOADING PROGRESS STATE */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-amber-200 dark:border-amber-900/50 shadow-md">
            <CardContent className="py-10 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto animate-pulse">
                <RefreshCw className="w-7 h-7 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  {stage === "uploading" ? "Uploading Document" : "Analyzing & Reconstructing PDF"}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">{statusMessage}</p>
              </div>

              {/* Progress Bar */}
              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-amber-600 h-3 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 font-medium">
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
            {!selectedFile ? (
              /* Dropzone */
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
                  isDragging
                    ? "border-amber-500 bg-amber-50/60 dark:bg-amber-950/30 scale-[1.01]"
                    : "border-gray-300 dark:border-gray-800 hover:border-amber-400 hover:bg-gray-50/50 dark:hover:bg-gray-900/40"
                }`}
              >
                <input
                  id="repair-file-input"
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  aria-label="Upload corrupted or damaged PDF file to repair"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileAdded(e.target.files);
                      e.target.value = "";
                    }
                  }}
                />

                <div className="flex flex-col items-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 flex items-center justify-center shadow-inner">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-base font-semibold text-gray-800 dark:text-gray-200">
                      Choose a PDF file or drag & drop it here
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Select 1 damaged or unreadable PDF document to analyze and reconstruct (max 50 MB).
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
              <Card className="shadow-sm border-amber-200/60 dark:border-amber-900/40">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <FileText className="w-4 h-4 text-amber-600" /> Selected Document
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Ready for structural recovery analysis.
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
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {formatBytes(selectedFile.size)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Non-destructive guarantee notice */}
                  <div className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-200">
                    <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">Safe, Non-Destructive Repair: </span>
                      DocForge reconstructs corrupted elements into a brand new PDF. Your original file is never overwritten or altered.
                    </div>
                  </div>

                  {/* Output Filename Customization */}
                  <div className="space-y-1.5 pt-1">
                    <label
                      htmlFor="output-filename-input"
                      className="text-xs font-medium text-gray-700 dark:text-gray-300 block"
                    >
                      Output Filename
                    </label>
                    <input
                      id="output-filename-input"
                      type="text"
                      value={outputFilename}
                      onChange={(e) => setOutputFilename(e.target.value)}
                      placeholder="repaired_document.pdf"
                      className="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  {/* Action Button */}
                  <div className="pt-2">
                    <Button
                      id="repair-action-btn"
                      onClick={startRepair}
                      size="lg"
                      className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold gap-2 shadow-lg shadow-amber-600/20"
                    >
                      <Wrench className="w-5 h-5" />
                      Repair PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* SEO Landing & How-To Section */}
        {seoData && <ToolSeoSection tool={seoData} />}
      </main>
    </div>
  );
}
