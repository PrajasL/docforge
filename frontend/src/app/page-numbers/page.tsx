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
  Hash,
  Sliders,
  Type,
  Layers,
  Sparkles,
  ShieldCheck,
  Eye,
  AlignLeft,
  AlignCenter,
  AlignRight,
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
  numberedPagesCount?: number;
  numberingFormat?: string;
  position?: string;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type PositionOption =
  | "top_left"
  | "top_center"
  | "top_right"
  | "bottom_left"
  | "bottom_center"
  | "bottom_right";

type FormatOption = "page_n_of_total" | "page_n" | "n" | "n_of_total";

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function PageNumbersPdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [position, setPosition] = useState<PositionOption>("bottom_center");
  const [format, setFormat] = useState<FormatOption>("page_n_of_total");
  const [startNumber, setStartNumber] = useState<number>(1);
  const [startPage, setStartPage] = useState<number>(1);
  const [fontSize, setFontSize] = useState<number>(12);
  const [color, setColor] = useState<string>("#374151");
  const [margin, setMargin] = useState<number>(36);
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
    setOutputFilename(`numbered_${baseName}.pdf`);
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

  // Compute preview sample label
  const getPreviewLabel = () => {
    const num = startNumber;
    const totalSample = 10;
    switch (format) {
      case "page_n":
        return `Page ${num}`;
      case "n":
        return `${num}`;
      case "n_of_total":
        return `${num} of ${totalSample}`;
      case "page_n_of_total":
      default:
        return `Page ${num} of ${totalSample}`;
    }
  };

  const startPageNumbers = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }

    if (startNumber < 1) {
      setErrorMessage("Starting number must be 1 or greater.");
      return;
    }

    if (startPage < 1) {
      setErrorMessage("Starting page must be 1 or greater.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Initializing page numbering job...");

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
          tool: "page_numbers",
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
      setStatusMessage("Starting page numbering engine...");

      // Step 3: Start job with page numbers config
      const finalName = outputFilename.trim() || `numbered_${selectedFile.name}`;
      const configPayload: Record<string, any> = {
        position,
        format,
        start_number: startNumber,
        start_page: startPage,
        font_size: fontSize,
        margin,
        color,
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
      setStatusMessage("Stamping page numbers onto document pages...");

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
            setStatusMessage("Applying page number layers to pages...");
          } else if (status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("completed");
            setStatusMessage("Page numbers added successfully!");

            const resFile = job.result_file;
            setResult({
              jobId: job.id,
              filename: resFile?.original_name || finalName,
              sizeBytes: resFile?.size_bytes || 0,
              pageCount: resFile?.page_count,
              numberedPagesCount: resFile?.numbered_pages_count,
              numberingFormat: resFile?.numbering_format || format,
              position: resFile?.position || position,
            });
          } else if (status === "FAILED") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(job.error_message || "Page numbering failed on server.");
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
      const msg = err instanceof Error ? err.message : "Unexpected error during page numbering.";
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
      setErrorMessage(err.message || "Failed to download numbered PDF.");
    }
  };

  const positionsList: { id: PositionOption; label: string; vAlign: "top" | "bottom"; hAlign: "left" | "center" | "right" }[] = [
    { id: "top_left", label: "Top Left", vAlign: "top", hAlign: "left" },
    { id: "top_center", label: "Top Center", vAlign: "top", hAlign: "center" },
    { id: "top_right", label: "Top Right", vAlign: "top", hAlign: "right" },
    { id: "bottom_left", label: "Bottom Left", vAlign: "bottom", hAlign: "left" },
    { id: "bottom_center", label: "Bottom Center", vAlign: "bottom", hAlign: "center" },
    { id: "bottom_right", label: "Bottom Right", vAlign: "bottom", hAlign: "right" },
  ];

  const formatsList: { id: FormatOption; label: string; sample: string }[] = [
    { id: "page_n_of_total", label: "Page X of Y", sample: "Page 1 of 10" },
    { id: "page_n", label: "Page X", sample: "Page 1" },
    { id: "n", label: "Number only", sample: "1" },
    { id: "n_of_total", label: "X of Y", sample: "1 of 10" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Navigation */}
      <ToolHeader toolName="Page Numbers" icon={Hash} iconBgColor="bg-teal-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner Info */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Add Page Numbers to PDF
          </h1>
          <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
            Stamp customizable page numbers onto your documents with accurate placement, custom formats, and starting offsets.
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
                ? "border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 scale-[1.01]"
                : "border-gray-300 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-700 bg-white dark:bg-gray-900"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4 shadow-inner">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Upload your PDF file</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-6 max-w-xs">
                Drag and drop your PDF here, or click browse to select a file from your computer.
              </p>
              <input
                id="page-numbers-file-input"
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                aria-label="Upload PDF file to add page numbers"
                onChange={(e) => e.target.files && handleFileAdded(e.target.files)}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20"
              >
                <FileText className="w-4 h-4 mr-2" />
                Choose PDF File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* File Config Area (if file selected) */}
        {selectedFile && (
          <div className="space-y-6">
            {/* Selected File Card */}
            <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
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

            {/* Config & Live Preview Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Settings Controls (7 cols) */}
              <div className="lg:col-span-7 space-y-6">
                <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm">
                  <CardHeader className="pb-4 border-b border-gray-100 dark:border-gray-800">
                    <CardTitle className="text-base font-semibold flex items-center">
                      <Sliders className="w-4 h-4 mr-2 text-indigo-600" />
                      Page Number Settings
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Configure positioning, numbering format, and starting offsets.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-5 space-y-5">
                    {/* Position Picker */}
                    <div className="space-y-2">
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Position on Page
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {positionsList.map((pos) => {
                          const isActive = position === pos.id;
                          return (
                            <button
                              key={pos.id}
                              id={`pos-${pos.id}-btn`}
                              type="button"
                              onClick={() => setPosition(pos.id)}
                              className={`p-2.5 rounded-lg border text-xs font-medium flex flex-col items-center justify-center transition-all ${
                                isActive
                                  ? "border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold shadow-sm"
                                  : "border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                              }`}
                            >
                              <span className="capitalize">{pos.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Numbering Format */}
                    <div className="space-y-2">
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Numbering Format
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {formatsList.map((fmt) => {
                          const isActive = format === fmt.id;
                          return (
                            <button
                              key={fmt.id}
                              id={`format-${fmt.id}-btn`}
                              type="button"
                              onClick={() => setFormat(fmt.id)}
                              className={`p-2.5 rounded-lg border text-left transition-all ${
                                isActive
                                  ? "border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 shadow-sm"
                                  : "border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                              }`}
                            >
                              <div className="text-xs font-semibold">{fmt.label}</div>
                              <div className="text-[11px] text-gray-500 dark:text-gray-400 font-mono mt-0.5">
                                {fmt.sample}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Starting Offsets */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">
                          Start on Page
                        </label>
                        <input
                          id="start-page-input"
                          type="number"
                          min="1"
                          value={startPage}
                          onChange={(e) => setStartPage(Math.max(1, parseInt(e.target.value) || 1))}
                          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                        <p className="text-[10px] text-gray-400 mt-0.5">Pages before this stay clean</p>
                      </div>

                      <div>
                        <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">
                          Starting Number
                        </label>
                        <input
                          id="start-number-input"
                          type="number"
                          min="1"
                          value={startNumber}
                          onChange={(e) => setStartNumber(Math.max(1, parseInt(e.target.value) || 1))}
                          className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                        <p className="text-[10px] text-gray-400 mt-0.5">e.g. 1, 5, or 100</p>
                      </div>
                    </div>

                    {/* Typography: Font Size & Color */}
                    <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
                      <div>
                        <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">
                          Font Size ({fontSize} pt)
                        </label>
                        <div className="flex items-center space-x-2">
                          <input
                            id="font-size-input"
                            type="range"
                            min="8"
                            max="28"
                            step="1"
                            value={fontSize}
                            onChange={(e) => setFontSize(parseInt(e.target.value))}
                            className="w-full accent-indigo-600"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">
                          Text Color
                        </label>
                        <div className="flex items-center space-x-2">
                          <input
                            id="color-picker-input"
                            type="color"
                            value={color}
                            onChange={(e) => setColor(e.target.value)}
                            className="w-8 h-8 rounded border border-gray-300 dark:border-gray-700 cursor-pointer p-0.5 bg-transparent"
                          />
                          <input
                            type="text"
                            value={color}
                            onChange={(e) => setColor(e.target.value)}
                            className="w-20 px-2 py-1 text-xs font-mono rounded border border-gray-300 dark:border-gray-700 uppercase"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Output Filename */}
                    <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1 block">
                        Output Filename
                      </label>
                      <input
                        id="output-filename-input"
                        type="text"
                        value={outputFilename}
                        onChange={(e) => setOutputFilename(e.target.value)}
                        placeholder="numbered_document.pdf"
                        className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Live Preview Panel (5 cols) */}
              <div className="lg:col-span-5 space-y-4">
                <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 shadow-sm sticky top-24">
                  <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800">
                    <CardTitle className="text-sm font-semibold flex items-center justify-between">
                      <span className="flex items-center">
                        <Eye className="w-4 h-4 mr-1.5 text-indigo-600" />
                        Live Page Preview
                      </span>
                      <span className="text-[11px] font-normal text-gray-500">
                        {position.replace("_", " ")}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 flex flex-col items-center justify-center">
                    {/* Simulated PDF Paper Sheet */}
                    <div className="w-52 h-72 bg-white rounded-md shadow-lg border border-gray-200 relative overflow-hidden flex flex-col justify-between p-4 transition-all">
                      {/* Top Bar Placement Area */}
                      <div className="w-full flex items-center justify-between text-xs font-medium">
                        <div
                          className={`transition-opacity ${
                            position === "top_left" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                        <div
                          className={`transition-opacity ${
                            position === "top_center" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                        <div
                          className={`transition-opacity ${
                            position === "top_right" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                      </div>

                      {/* Mock Content Lines */}
                      <div className="space-y-2 opacity-25 px-1 py-4">
                        <div className="h-2 bg-gray-400 rounded w-3/4"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-full"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-5/6"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-full"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-2/3"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-4/5 mt-4"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-full"></div>
                        <div className="h-1.5 bg-gray-300 rounded w-1/2"></div>
                      </div>

                      {/* Bottom Bar Placement Area */}
                      <div className="w-full flex items-center justify-between text-xs font-medium">
                        <div
                          className={`transition-opacity ${
                            position === "bottom_left" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                        <div
                          className={`transition-opacity ${
                            position === "bottom_center" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                        <div
                          className={`transition-opacity ${
                            position === "bottom_right" ? "opacity-100 font-bold" : "opacity-0"
                          }`}
                          style={{ color, fontSize: `${Math.min(fontSize, 14)}px` }}
                        >
                          {getPreviewLabel()}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 text-center text-[11px] text-gray-500 dark:text-gray-400">
                      Sample preview format: <span className="font-mono font-semibold">{getPreviewLabel()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Action / Progress Area */}
            <div className="pt-2">
              {stage === "idle" && (
                <Button
                  id="start-page-numbers-btn"
                  onClick={startPageNumbers}
                  className="w-full py-6 text-base font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/20"
                >
                  <Hash className="w-5 h-5 mr-2" />
                  Add Page Numbers to PDF
                </Button>
              )}

              {(stage === "uploading" || stage === "processing") && (
                <Card className="bg-white dark:bg-gray-900 border-indigo-200 dark:border-indigo-900/60 shadow-md">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <RefreshCw className="w-4 h-4 text-indigo-600 animate-spin" />
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {statusMessage}
                        </span>
                      </div>
                      <span className="text-xs font-bold text-indigo-600">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
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
                          Page Numbers Successfully Added!
                        </h4>
                        <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
                          Document is stamped and ready for download.
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-white/70 dark:bg-gray-900/70 rounded-lg border border-emerald-100 dark:border-emerald-900/50 text-xs">
                      <div>
                        <span className="text-gray-500 block">Total Pages</span>
                        <span className="font-semibold">{result.pageCount ?? "N/A"}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Numbered Pages</span>
                        <span className="font-semibold text-indigo-600">
                          {result.numberedPagesCount ?? "N/A"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Position</span>
                        <span className="font-semibold capitalize">
                          {result.position?.replace("_", " ") ?? "Bottom center"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Output Size</span>
                        <span className="font-semibold">{formatBytes(result.sizeBytes)}</span>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3 pt-2">
                      <Button
                        id="download-result-btn"
                        onClick={handleDownload}
                        className="flex-1 py-5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-600/20"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Numbered PDF
                      </Button>
                      <Button
                        variant="outline"
                        onClick={clearSelection}
                        className="border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        Number Another PDF
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("page-numbers")!} />
      </main>
    </div>
  );
}
