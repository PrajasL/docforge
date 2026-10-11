"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
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
  Copy,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Undo2,
  CheckSquare,
  Square,
  Sparkles,
  Layers,
  FileCheck,
  LayoutGrid,
} from "lucide-react";
import { countPdfPages } from "@/app/extract-pages/page";
import { ToolSeoSection } from "@/components/tool-seo-section";
import { getToolSeoData } from "@/config/tools-seo";


export interface PageItem {
  id: string;
  originalPageNumber: number;
  rotation: number;
  thumbnailUrl?: string | null;
  selected?: boolean;
}

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

export default function OrganizePdfPage() {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [pages, setPages] = useState<PageItem[]>([]);
  const [initialPages, setInitialPages] = useState<PageItem[]>([]);
  const [history, setHistory] = useState<PageItem[][]>([]);
  const [outputFilename, setOutputFilename] = useState<string>("");
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResultData | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState<boolean>(false);
  const [isLoadingPages, setIsLoadingPages] = useState<boolean>(false);

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

  // Push state to undo history before making mutations
  const updatePagesWithHistory = useCallback(
    (updater: (prev: PageItem[]) => PageItem[]) => {
      setPages((prev) => {
        const next = updater(prev);
        // Only record if content changed
        if (JSON.stringify(prev) !== JSON.stringify(next)) {
          setHistory((h) => [...h.slice(-15), prev]);
        }
        return next;
      });
    },
    []
  );

  const loadPdfThumbnails = async (file: File) => {
    setIsLoadingPages(true);
    try {
      const arrayBuffer = await file.arrayBuffer();
      let generatedPages: PageItem[] = [];

      // Try PDF.js rendering in browser environment
      if (typeof window !== "undefined") {
        try {
          const pdfjs = await import("pdfjs-dist");
          const getDocument = pdfjs.getDocument || (pdfjs as any).default?.getDocument;
          const GlobalWorkerOptions = pdfjs.GlobalWorkerOptions || (pdfjs as any).default?.GlobalWorkerOptions;
          if (GlobalWorkerOptions) {
            GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
          }

          if (getDocument) {
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
            const numPages = doc.numPages;

            for (let i = 1; i <= numPages; i++) {
              let thumbUrl: string | null = null;
              try {
                const page = await doc.getPage(i);
                const viewport = page.getViewport({ scale: 0.35 });
                const canvas = document.createElement("canvas");
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                const ctx = canvas.getContext("2d");
                if (ctx) {
                  await page.render({ canvas, canvasContext: ctx, viewport }).promise;
                  thumbUrl = canvas.toDataURL("image/jpeg", 0.8);
                }
              } catch {
                thumbUrl = null;
              }

              generatedPages.push({
                id: crypto.randomUUID(),
                originalPageNumber: i,
                rotation: 0,
                thumbnailUrl: thumbUrl,
                selected: false,
              });
            }
          }
        } catch {
          // PDF.js worker or render unavailable
        }
      }

      // If PDF.js did not populate pages (e.g. unit test JSDOM or worker error), fall back to countPdfPages
      if (generatedPages.length === 0) {
        const count = await countPdfPages(file);
        if (count && count > 0) {
          for (let i = 1; i <= count; i++) {
            generatedPages.push({
              id: crypto.randomUUID(),
              originalPageNumber: i,
              rotation: 0,
              thumbnailUrl: null,
              selected: false,
            });
          }
        } else {
          setErrorMessage("Could not parse PDF pages. The file might be corrupted or password-protected.");
          setSelectedFile(null);
          return;
        }
      }

      setPages(generatedPages);
      setInitialPages(JSON.parse(JSON.stringify(generatedPages)));
      setHistory([]);
    } catch {
      setErrorMessage("Could not parse PDF pages. The file might be corrupted or password-protected.");
    } finally {
      setIsLoadingPages(false);
    }
  };

  const handleFileAdded = (incoming: FileList | File[]) => {
    if (!incoming || incoming.length === 0) return;
    const file = incoming[0];

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage(`Skipped non-PDF file: ${file.name}. Only PDF files are supported.`);
      return;
    }

    setErrorMessage(null);
    const baseName = file.name.replace(/\.pdf$/i, "");
    setOutputFilename(`organized_${baseName}.pdf`);

    setSelectedFile({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
    });

    loadPdfThumbnails(file);
  };

  const handleDragOverFile = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(true);
  };

  const handleDragLeaveFile = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(false);
  };

  const handleDropFile = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileAdded(e.dataTransfer.files);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setPages([]);
    setInitialPages([]);
    setHistory([]);
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

  // --- Page Editing Actions ---
  const rotatePage = (index: number) => {
    updatePagesWithHistory((prev) =>
      prev.map((p, idx) => (idx === index ? { ...p, rotation: (p.rotation + 90) % 360 } : p))
    );
  };

  const duplicatePage = (index: number) => {
    updatePagesWithHistory((prev) => {
      const target = prev[index];
      const copy: PageItem = {
        ...target,
        id: crypto.randomUUID(),
        selected: false,
      };
      const updated = [...prev];
      updated.splice(index + 1, 0, copy);
      return updated;
    });
  };

  const deletePage = (index: number) => {
    if (pages.length <= 1) {
      setErrorMessage("At least one page must remain in the organized PDF.");
      return;
    }
    setErrorMessage(null);
    updatePagesWithHistory((prev) => prev.filter((_, idx) => idx !== index));
  };

  const movePage = (fromIndex: number, toIndex: number) => {
    if (toIndex < 0 || toIndex >= pages.length || fromIndex === toIndex) return;
    updatePagesWithHistory((prev) => {
      const updated = [...prev];
      const [moved] = updated.splice(fromIndex, 1);
      updated.splice(toIndex, 0, moved);
      return updated;
    });
  };

  // Drag and drop page reordering
  const handlePageDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  const handlePageDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handlePageDrop = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== index) {
      movePage(draggedIndex, index);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handlePageDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Selection controls
  const toggleSelectPage = (index: number) => {
    setPages((prev) =>
      prev.map((p, idx) => (idx === index ? { ...p, selected: !p.selected } : p))
    );
  };

  const selectAllPages = () => {
    setPages((prev) => prev.map((p) => ({ ...p, selected: true })));
  };

  const deselectAllPages = () => {
    setPages((prev) => prev.map((p) => ({ ...p, selected: false })));
  };

  const rotateSelectedPages = () => {
    const hasSelected = pages.some((p) => p.selected);
    if (!hasSelected) return;
    updatePagesWithHistory((prev) =>
      prev.map((p) => (p.selected ? { ...p, rotation: (p.rotation + 90) % 360 } : p))
    );
  };

  const deleteSelectedPages = () => {
    const remainingCount = pages.filter((p) => !p.selected).length;
    if (remainingCount === 0) {
      setErrorMessage("Cannot delete all pages. At least one page must remain.");
      return;
    }
    setErrorMessage(null);
    updatePagesWithHistory((prev) => prev.filter((p) => !p.selected));
  };

  // Undo & Reset
  const handleUndo = () => {
    if (history.length === 0) return;
    const previousState = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setPages(previousState);
  };

  const handleReset = () => {
    if (initialPages.length === 0) return;
    updatePagesWithHistory(() => JSON.parse(JSON.stringify(initialPages)));
  };

  // --- Processing ---
  const startOrganizing = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }
    if (pages.length === 0) {
      setErrorMessage("At least one page must be included in the organized PDF.");
      return;
    }

    setErrorMessage(null);
    setStage("uploading");
    setProgress(5);
    setStatusMessage("Creating organization job...");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // 1. Create job
      const createResp = await fetch(`${apiUrl}/api/v1/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionIdRef.current,
        },
        body: JSON.stringify({
          tool: "organize_pdf",
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

      if (!createResp.ok) {
        const errJson = await createResp.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.message || "Failed to initialize organization job.");
      }

      const createData = await createResp.json();
      const jobId = createData.data.job.id;
      const fileId = createData.data.uploads[0].file_id;

      // 2. Upload input PDF
      setStatusMessage("Uploading document...");
      setProgress(25);

      const uploadResp = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/files/${fileId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/pdf",
          "X-Session-Id": sessionIdRef.current,
        },
        body: selectedFile.file,
      });

      if (!uploadResp.ok) {
        const errJson = await uploadResp.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.message || "Failed to upload document.");
      }

      // 3. Start processing with page configuration
      setStatusMessage("Starting PDF organization...");
      setProgress(40);
      setStage("processing");

      const pagesPayload = pages.map((p) => ({
        page_number: p.originalPageNumber,
        rotation: p.rotation,
      }));

      const startResp = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionIdRef.current,
        },
        body: JSON.stringify({
          config: {
            pages: pagesPayload,
            output_filename: outputFilename.trim() || `organized_${selectedFile.name}`,
          },
        }),
      });

      if (!startResp.ok) {
        const errJson = await startResp.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.message || "Failed to start organization.");
      }

      // 4. Poll job status
      const maxAttempts = 60;
      let attempts = 0;

      const poll = async () => {
        attempts++;
        try {
          const statusResp = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, {
            headers: { "X-Session-Id": sessionIdRef.current },
          });

          if (!statusResp.ok) {
            throw new Error("Failed to check processing status.");
          }

          const statusData = await statusResp.json();
          const job = statusData.data?.job || statusData.data;
          const status = (job?.status || "").toUpperCase();

          if (status === "COMPLETED") {
            setProgress(100);
            setStatusMessage("Organization completed!");
            setStage("completed");
            setResult({
              jobId,
              filename: job.result_file?.original_name || outputFilename || "organized_document.pdf",
              sizeBytes: job.result_file?.size_bytes || 0,
              pageCount: job.result_file?.page_count || pages.length,
            });
            return;
          } else if (status === "FAILED") {
            throw new Error(job.error_message || "PDF organization failed.");
          } else {
            const currentProg = Math.max(40, Math.min(95, job.progress || 50));
            setProgress(currentProg);
            setStatusMessage("Reordering, rotating, and compiling PDF pages...");
            if (attempts < maxAttempts) {
              setTimeout(poll, 1000);
            } else {
              throw new Error("Organization timed out. Please try again.");
            }
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Error while checking job status";
          setStage("error");
          setErrorMessage(msg);
        }
      };

      setTimeout(poll, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setStage("error");
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
      const downloadUrl = json.data?.download_url;

      if (!downloadUrl) {
        throw new Error("No download URL returned by server.");
      }

      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", result.filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to download output PDF.";
      setErrorMessage(msg);
    }
  };

  const selectedCount = pages.filter((p) => p.selected).length;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="Organize PDF" icon={LayoutGrid} iconBgColor="bg-sky-600" />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Page Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            Organize PDF
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm sm:text-base">
            Visual page reordering, rotation, duplication, and deletion
          </p>
        </div>

        {/* Global Error Banner */}
        {errorMessage && (
          <div
            id="global-error-banner"
            role="alert"
            className="flex items-start space-x-3 p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800/80 rounded-xl text-red-800 dark:text-red-200 animate-in fade-in slide-in-from-top-2 duration-200"
          >
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm font-medium">{errorMessage}</div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-red-600 hover:text-red-800 dark:text-red-400 font-semibold underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Upload Dropzone (shown when idle and no file selected) */}
        {!selectedFile && stage === "idle" && (
          <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-500 bg-white dark:bg-slate-900 transition-colors shadow-sm">
            <CardContent className="p-8 sm:p-12">
              <div
                onDragOver={handleDragOverFile}
                onDragLeave={handleDragLeaveFile}
                onDrop={handleDropFile}
                className={`flex flex-col items-center justify-center text-center space-y-4 p-8 rounded-xl transition-all ${
                  isDraggingFile
                    ? "bg-blue-50/80 dark:bg-blue-950/40 border-2 border-blue-500 scale-[1.01]"
                    : ""
                }`}
              >
                <div className="w-16 h-16 rounded-2xl bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-blue-600 dark:text-blue-400 shadow-inner">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-xl font-bold tracking-tight">Choose a PDF to organize</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm">
                    Drag and drop your PDF here, or browse your local files
                  </p>
                </div>
                <input
                  id="pdf-upload-input"
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  aria-label="Upload PDF file to organize"
                  onChange={(e) => handleFileAdded(e.target.files!)}
                />
                <Button
                  id="select-file-btn"
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-md px-6 py-2"
                >
                  Select PDF File
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading Spinner for Thumbnail Extraction */}
        {selectedFile && isLoadingPages && (
          <div className="text-center py-12 space-y-3">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
            <p className="text-sm text-slate-500 font-medium">Rendering PDF page thumbnails...</p>
          </div>
        )}

        {/* Visual Organize Editor */}
        {selectedFile && !isLoadingPages && stage === "idle" && (
          <div className="space-y-6">
            {/* File Info & Global Action Bar */}
            <Card className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm">
              <CardContent className="p-4 sm:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 dark:text-slate-100 truncate max-w-xs sm:max-w-md">
                        {selectedFile.name}
                      </h4>
                      <p className="text-xs text-slate-500">
                        {formatBytes(selectedFile.size)} • {pages.length} {pages.length === 1 ? "page" : "pages"} in
                        result
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      id="change-file-btn"
                      variant="outline"
                      size="sm"
                      onClick={clearSelection}
                      className="text-xs text-slate-600 dark:text-slate-300"
                    >
                      Change File
                    </Button>
                  </div>
                </div>

                {/* Toolbar: Undo, Reset, Selection Controls */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Select All / Deselect All */}
                    {selectedCount < pages.length ? (
                      <Button
                        id="select-all-btn"
                        variant="outline"
                        size="sm"
                        onClick={selectAllPages}
                        className="text-xs flex items-center gap-1.5"
                      >
                        <CheckSquare className="w-3.5 h-3.5" />
                        Select All
                      </Button>
                    ) : (
                      <Button
                        id="deselect-all-btn"
                        variant="outline"
                        size="sm"
                        onClick={deselectAllPages}
                        className="text-xs flex items-center gap-1.5"
                      >
                        <Square className="w-3.5 h-3.5" />
                        Deselect All
                      </Button>
                    )}

                    {/* Batch Actions on Selection */}
                    {selectedCount > 0 && (
                      <>
                        <Button
                          id="rotate-selected-btn"
                          variant="outline"
                          size="sm"
                          onClick={rotateSelectedPages}
                          className="text-xs flex items-center gap-1.5 text-blue-600 hover:text-blue-700"
                        >
                          <RotateCw className="w-3.5 h-3.5" />
                          Rotate Selected ({selectedCount})
                        </Button>
                        <Button
                          id="delete-selected-btn"
                          variant="outline"
                          size="sm"
                          onClick={deleteSelectedPages}
                          className="text-xs flex items-center gap-1.5 text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Delete Selected ({selectedCount})
                        </Button>
                      </>
                    )}
                  </div>

                  {/* History Controls */}
                  <div className="flex items-center gap-2">
                    <Button
                      id="undo-btn"
                      variant="outline"
                      size="sm"
                      onClick={handleUndo}
                      disabled={history.length === 0}
                      className="text-xs flex items-center gap-1.5"
                      title="Undo last change"
                    >
                      <Undo2 className="w-3.5 h-3.5" />
                      Undo
                    </Button>
                    <Button
                      id="reset-btn"
                      variant="outline"
                      size="sm"
                      onClick={handleReset}
                      className="text-xs flex items-center gap-1.5 text-slate-500 hover:text-slate-800"
                      title="Reset to original PDF"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reset
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Thumbnails Grid with Drag & Drop */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 px-1">
                <span>Drag cards to reorder. Use per-page buttons to rotate, duplicate, or delete.</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  {pages.length} {pages.length === 1 ? "Page" : "Pages"}
                </span>
              </div>

              <div
                id="pages-grid"
                className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
              >
                {pages.map((item, idx) => {
                  const isDragged = draggedIndex === idx;
                  const isDropOver = dragOverIndex === idx;

                  return (
                    <div
                      key={item.id}
                      data-testid="page-card"
                      draggable
                      onDragStart={(e) => handlePageDragStart(e, idx)}
                      onDragOver={(e) => handlePageDragOver(e, idx)}
                      onDrop={(e) => handlePageDrop(e, idx)}
                      onDragEnd={handlePageDragEnd}
                      className={`relative group bg-white dark:bg-slate-900 border rounded-xl p-3 flex flex-col items-center transition-all cursor-grab active:cursor-grabbing select-none shadow-sm hover:shadow-md ${
                        item.selected
                          ? "border-blue-500 ring-2 ring-blue-500/20"
                          : "border-slate-200 dark:border-slate-800 hover:border-slate-400"
                      } ${isDragged ? "opacity-30 scale-95" : ""} ${
                        isDropOver ? "border-blue-500 border-2 scale-105" : ""
                      }`}
                    >
                      {/* Top Header: Checkbox & Current Order Number */}
                      <div className="w-full flex items-center justify-between mb-2">
                        <button
                          type="button"
                          data-testid="select-page-checkbox"
                          onClick={() => toggleSelectPage(idx)}
                          className="text-slate-400 hover:text-blue-600 focus:outline-none"
                          title={item.selected ? "Deselect page" : "Select page"}
                        >
                          {item.selected ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          #{idx + 1}
                        </span>
                      </div>

                      {/* Thumbnail or Card Canvas */}
                      <div className="w-full h-36 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-100 dark:border-slate-800 flex items-center justify-center overflow-hidden relative mb-3">
                        {item.thumbnailUrl ? (
                          <img
                            src={item.thumbnailUrl}
                            alt={`Page ${item.originalPageNumber}`}
                            className="max-h-full max-w-full object-contain transition-transform duration-200"
                            style={{ transform: `rotate(${item.rotation}deg)` }}
                          />
                        ) : (
                          <div
                            className="flex flex-col items-center justify-center p-2 text-slate-400 transition-transform duration-200"
                            style={{ transform: `rotate(${item.rotation}deg)` }}
                          >
                            <FileText className="w-10 h-10 mb-1 opacity-70" />
                            <span className="text-[10px] font-semibold">Page {item.originalPageNumber}</span>
                          </div>
                        )}

                        {/* Rotation Tag if rotated */}
                        {item.rotation !== 0 && (
                          <span className="absolute bottom-1 right-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-600 text-white shadow">
                            +{item.rotation}°
                          </span>
                        )}
                      </div>

                      {/* Original Page Reference */}
                      <div className="text-[11px] text-slate-400 mb-2">
                        Original: Page {item.originalPageNumber}
                      </div>

                      {/* Per-Page Quick Action Buttons */}
                      <div className="flex items-center justify-center gap-1 w-full pt-1 border-t border-slate-100 dark:border-slate-800">
                        {/* Move Left */}
                        <button
                          type="button"
                          data-testid="move-left-btn"
                          onClick={() => movePage(idx, idx - 1)}
                          disabled={idx === 0}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 disabled:opacity-20"
                          title="Move left"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                        </button>

                        {/* Rotate +90 */}
                        <button
                          type="button"
                          data-testid="rotate-page-btn"
                          onClick={() => rotatePage(idx)}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-blue-600"
                          title="Rotate +90° clockwise"
                        >
                          <RotateCw className="w-3.5 h-3.5" />
                        </button>

                        {/* Duplicate */}
                        <button
                          type="button"
                          data-testid="duplicate-page-btn"
                          onClick={() => duplicatePage(idx)}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-indigo-600"
                          title="Duplicate page"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>

                        {/* Delete */}
                        <button
                          type="button"
                          data-testid="delete-page-btn"
                          onClick={() => deletePage(idx)}
                          disabled={pages.length <= 1}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-red-600 disabled:opacity-20"
                          title="Delete page"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>

                        {/* Move Right */}
                        <button
                          type="button"
                          data-testid="move-right-btn"
                          onClick={() => movePage(idx, idx + 1)}
                          disabled={idx === pages.length - 1}
                          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 disabled:opacity-20"
                          title="Move right"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Export Settings & Action Box */}
            <Card className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div>
                  <label
                    htmlFor="output-filename-input"
                    className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2"
                  >
                    Custom Output Filename
                  </label>
                  <input
                    id="output-filename-input"
                    type="text"
                    value={outputFilename}
                    onChange={(e) => setOutputFilename(e.target.value)}
                    placeholder="organized_document.pdf"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="pt-2">
                  <Button
                    id="organize-submit-btn"
                    onClick={startOrganizing}
                    disabled={pages.length === 0}
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-3 text-base shadow-lg hover:shadow-xl transition-all"
                  >
                    Compile & Organize PDF ({pages.length} {pages.length === 1 ? "Page" : "Pages"})
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Processing State */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-md">
            <CardContent className="p-8 space-y-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400 mx-auto animate-pulse">
                <RefreshCw className="w-8 h-8 animate-spin" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold tracking-tight">Organizing Document</h3>
                <p className="text-sm text-slate-500">{statusMessage}</p>
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Completed State */}
        {stage === "completed" && result && (
          <Card className="border-emerald-200 dark:border-emerald-900 bg-white dark:bg-slate-900 shadow-lg">
            <CardContent className="p-8 space-y-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h3 className="text-2xl font-black text-slate-900 dark:text-slate-100">
                  PDF Organized Successfully!
                </h3>
                <p className="text-sm text-slate-500">
                  Your PDF with {result.pageCount} pages is ready for download.
                </p>
              </div>

              <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 max-w-md mx-auto text-left space-y-2 text-sm border border-slate-100 dark:border-slate-800">
                <div className="flex justify-between">
                  <span className="text-slate-500">File Name:</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
                    {result.filename}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">File Size:</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {formatBytes(result.sizeBytes)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Pages in Output:</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{result.pageCount}</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
                <Button
                  id="download-btn"
                  onClick={handleDownload}
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-md hover:shadow-lg transition-all gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download Organized PDF
                </Button>
                <Button
                  id="organize-another-btn"
                  variant="outline"
                  onClick={clearSelection}
                  className="w-full sm:w-auto px-6 py-3"
                >
                  Organize Another PDF
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("organize-pdf")!} />
      </main>
    </div>
  );
}
