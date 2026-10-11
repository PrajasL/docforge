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
  Image as ImageIcon,
  Info,
  Check,
  Layers,
  Sparkles,
  Sliders,
  ShieldCheck,
  ArrowUp,
  ArrowDown,
  GripVertical,
  Plus,
} from "lucide-react";
import { ToolSeoSection } from "@/components/tool-seo-section";
import { getToolSeoData } from "@/config/tools-seo";


interface ImageItem {
  id: string;
  file: File;
  name: string;
  size: number;
  previewUrl: string;
  width?: number;
  height?: number;
}

interface ResultData {
  jobId: string;
  filename: string;
  sizeBytes: number;
  pageCount: number;
  fileCount: number;
}

type Stage = "idle" | "uploading" | "processing" | "completed" | "error";
type OrientationOption = "auto" | "portrait" | "landscape";
type PageSizeOption = "fit" | "a4" | "letter";
type MarginOption = "none" | "small" | "normal";

const MAX_FILES = 50;
const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export default function JpgToPdfPage() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [orientation, setOrientation] = useState<OrientationOption>("auto");
  const [pageSize, setPageSize] = useState<PageSizeOption>("fit");
  const [margin, setMargin] = useState<MarginOption>("none");
  const [outputFilename, setOutputFilename] = useState<string>("");

  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ResultData | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Drag and drop reordering state
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

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

  // Clean up Object URLs on unmount
  useEffect(() => {
    return () => {
      images.forEach((img) => {
        if (img.previewUrl) {
          URL.revokeObjectURL(img.previewUrl);
        }
      });
    };
  }, [images]);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    if (!incoming || incoming.length === 0) return;

    setErrorMessage(null);
    const newItems: ImageItem[] = [];
    const rejectedNonJpg: string[] = [];
    const rejectedEmpty: string[] = [];
    const rejectedOversized: string[] = [];

    Array.from(incoming).forEach((file) => {
      const lowerName = file.name.toLowerCase();
      const isJpgExt = lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg");
      const isJpgMime = file.type === "image/jpeg" || file.type === "image/jpg";

      if (!isJpgExt && !isJpgMime) {
        rejectedNonJpg.push(file.name);
        return;
      }

      if (file.size === 0) {
        rejectedEmpty.push(file.name);
        return;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        rejectedOversized.push(file.name);
        return;
      }

      const previewUrl = URL.createObjectURL(file);
      const item: ImageItem = {
        id: crypto.randomUUID(),
        file,
        name: file.name,
        size: file.size,
        previewUrl,
      };

      // Measure dimensions asynchronously
      const imgObj = new Image();
      imgObj.onload = () => {
        setImages((prev) =>
          prev.map((it) =>
            it.id === item.id ? { ...it, width: imgObj.width, height: imgObj.height } : it
          )
        );
      };
      imgObj.src = previewUrl;

      newItems.push(item);
    });

    if (rejectedNonJpg.length > 0) {
      setErrorMessage(`Only JPG/JPEG images are accepted. Skipped: ${rejectedNonJpg.join(", ")}`);
    } else if (rejectedEmpty.length > 0) {
      setErrorMessage(`Cannot convert empty files (0 bytes): ${rejectedEmpty.join(", ")}`);
    } else if (rejectedOversized.length > 0) {
      setErrorMessage(
        `Files exceed maximum ${MAX_FILE_SIZE_MB} MB limit: ${rejectedOversized.join(", ")}`
      );
    }

    setImages((prev) => {
      const combined = [...prev, ...newItems];
      if (combined.length > MAX_FILES) {
        setErrorMessage(
          `Maximum ${MAX_FILES} images allowed per job. Retained first ${MAX_FILES} files.`
        );
        return combined.slice(0, MAX_FILES);
      }
      return combined;
    });
  }, []);

  const removeImage = (id: string) => {
    setImages((prev) => {
      const target = prev.find((it) => it.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((it) => it.id !== id);
    });
  };

  const moveImage = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
    setImages((prev) => {
      if (fromIndex >= prev.length || toIndex >= prev.length) return prev;
      const copy = [...prev];
      const [moved] = copy.splice(fromIndex, 1);
      copy.splice(toIndex, 0, moved);
      return copy;
    });
  };

  const clearAll = () => {
    images.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    setImages([]);
    setStage("idle");
    setResult(null);
    setErrorMessage(null);
    setProgress(0);
    setOutputFilename("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Drag and drop handlers for upload zone
  const handleZoneDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleZoneDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleZoneDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  // Card reordering drag handlers
  const handleCardDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleCardDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleCardDrop = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== index) {
      moveImage(draggedIndex, index);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleCardDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleConvert = async () => {
    if (images.length === 0) {
      setErrorMessage("Please select at least one JPG image to convert.");
      return;
    }

    setStage("uploading");
    setErrorMessage(null);
    setProgress(5);
    setStatusMessage("Creating conversion job...");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // Step 1: Create Job
      const filesPayload = images.map((img) => ({
        name: img.name,
        size: img.size,
        content_type: "image/jpeg",
      }));

      const finalFilename =
        outputFilename.trim() !== ""
          ? outputFilename.trim().toLowerCase().endsWith(".pdf")
            ? outputFilename.trim()
            : `${outputFilename.trim()}.pdf`
          : "converted_images.pdf";

      const configPayload = {
        orientation,
        page_size: pageSize,
        margin,
        output_filename: finalFilename,
      };

      const createRes = await fetch(`${apiUrl}/api/v1/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionIdRef.current,
        },
        body: JSON.stringify({
          tool: "jpg_to_pdf",
          files: filesPayload,
          config: configPayload,
        }),
      });

      const createData = await createRes.json();
      if (!createRes.ok) {
        throw new Error(createData.message || createData.detail || "Failed to create conversion job.");
      }

      const jobId = createData.data.job.id;
      const uploads = createData.data.uploads as Array<{
        file_id: string;
        upload_url: string;
        upload_method: string;
        upload_headers: Record<string, string>;
      }>;

      // Step 2: Upload Files (in user sequence)
      for (let i = 0; i < images.length; i++) {
        const item = images[i];
        const uploadMeta = uploads[i];
        const uploadProgress = 10 + Math.round(((i + 1) / images.length) * 35);
        setProgress(uploadProgress);
        setStatusMessage(`Uploading image ${i + 1} of ${images.length} (${item.name})...`);

        let uploadSucceeded = false;

        // Try direct presigned PUT
        try {
          const s3PutRes = await fetch(uploadMeta.upload_url, {
            method: uploadMeta.upload_method,
            headers: uploadMeta.upload_headers || { "Content-Type": "image/jpeg" },
            body: item.file,
          });

          if (s3PutRes.ok) {
            // Confirm presigned upload
            const confirmRes = await fetch(
              `${apiUrl}/api/v1/jobs/${jobId}/files/${uploadMeta.file_id}/confirm`,
              {
                method: "POST",
                headers: { "X-Session-ID": sessionIdRef.current },
              }
            );
            if (confirmRes.ok) {
              uploadSucceeded = true;
            }
          }
        } catch {
          uploadSucceeded = false;
        }

        // Fallback to direct API upload
        if (!uploadSucceeded) {
          const directPutRes = await fetch(
            `${apiUrl}/api/v1/jobs/${jobId}/files/${uploadMeta.file_id}`,
            {
              method: "PUT",
              headers: {
                "Content-Type": "image/jpeg",
                "X-Session-ID": sessionIdRef.current,
              },
              body: item.file,
            }
          );
          if (!directPutRes.ok) {
            const errData = await directPutRes.json();
            throw new Error(errData.message || `Failed to upload image ${item.name}.`);
          }
        }
      }

      // Step 3: Start Job with final ordering
      setStage("processing");
      setProgress(50);
      setStatusMessage("Starting PDF generation...");

      const orderedFileIds = uploads.map((u) => u.file_id);

      const startRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionIdRef.current,
        },
        body: JSON.stringify({
          config: {
            ...configPayload,
            file_order: orderedFileIds,
          },
        }),
      });

      const startData = await startRes.json();
      if (!startRes.ok) {
        throw new Error(startData.message || startData.detail || "Failed to start processing.");
      }

      // Step 4: Poll Job Status
      let isDone = false;
      let attempts = 0;
      const maxAttempts = 120; // 60 seconds

      while (!isDone && attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 600));
        attempts++;

        const pollRes = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, {
          headers: { "X-Session-ID": sessionIdRef.current },
        });

        if (!pollRes.ok) continue;

        const pollData = await pollRes.json();
        const job = pollData.data?.job || pollData.data;
        const status = (job?.status || "").toUpperCase();

        if (status === "PROCESSING") {
          const curProg = Math.max(55, Math.min(95, job.progress || 60));
          setProgress(curProg);
          setStatusMessage("Rendering pages and assembling PDF...");
        } else if (status === "COMPLETED") {
          isDone = true;
          setProgress(100);
          setStage("completed");
          setStatusMessage("Conversion complete!");
          setResult({
            jobId: job.id,
            filename: job.result_file?.original_name || finalFilename,
            sizeBytes: job.result_file?.size_bytes || 0,
            pageCount: job.result_file?.page_count || images.length,
            fileCount: job.result_file?.file_count || images.length,
          });
          break;
        } else if (status === "FAILED") {
          throw new Error(job.error_message || "Conversion failed on server.");
        }
      }

      if (!isDone) {
        throw new Error("Job timed out while processing. Please try again.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setStage("error");
      setErrorMessage(msg);
      setStatusMessage("");
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const sessionId = sessionIdRef.current;

    try {
      const res = await fetch(`${apiUrl}/api/v1/jobs/${result.jobId}/download`, {
        headers: {
          "X-Session-ID": sessionId,
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
      link.download = result.filename || "converted_images.pdf";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate download.";
      setErrorMessage(msg);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col">
      {/* Top Header */}
      <ToolHeader toolName="JPG to PDF" icon={ImageIcon} iconBgColor="bg-orange-600" />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8">
        {/* Page Hero */}
        <div className="text-center space-y-2 mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900 dark:text-gray-50">
            JPG to PDF
          </h1>
          <p className="text-gray-600 dark:text-gray-400 max-w-lg mx-auto text-sm sm:text-base">
            Convert multiple images to a unified PDF
          </p>
        </div>
        {/* Error Alert */}
        {errorMessage && (
          <div
            id="jpg-to-pdf-error-banner"
            role="alert"
            className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 flex items-start gap-3 shadow-sm animate-in fade-in duration-200"
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
            <div className="flex-1 text-sm font-medium">{errorMessage}</div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-500 hover:text-red-700 text-sm font-bold ml-2"
              title="Dismiss error"
            >
              &times;
            </button>
          </div>
        )}

        {/* COMPLETED STAGE */}
        {stage === "completed" && result && (
          <Card className="border-emerald-200 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-md mb-8">
            <CardHeader className="text-center pb-4">
              <div className="w-14 h-14 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                PDF Generated Successfully!
              </CardTitle>
              <CardDescription className="text-gray-600 dark:text-gray-400">
                Your images were combined into a downloadable PDF document.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-emerald-100 dark:border-emerald-900/50 shadow-sm grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                    Output File
                  </div>
                  <div
                    className="font-semibold text-sm truncate mt-1 text-gray-800 dark:text-gray-200"
                    title={result.filename}
                  >
                    {result.filename}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                    Total Pages
                  </div>
                  <div className="font-semibold text-sm mt-1 text-gray-800 dark:text-gray-200">
                    {result.pageCount} {result.pageCount === 1 ? "page" : "pages"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                    Images Converted
                  </div>
                  <div className="font-semibold text-sm mt-1 text-gray-800 dark:text-gray-200">
                    {result.fileCount} images
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                    PDF Size
                  </div>
                  <div className="font-semibold text-sm mt-1 text-gray-800 dark:text-gray-200">
                    {formatBytes(result.sizeBytes)}
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button
                  onClick={handleDownload}
                  size="lg"
                  className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-8 shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download PDF
                </Button>
                <Button
                  variant="outline"
                  onClick={clearAll}
                  size="lg"
                  className="w-full sm:w-auto"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Convert More Images
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PROCESSING / UPLOADING STAGE */}
        {(stage === "uploading" || stage === "processing") && (
          <Card className="border-gray-200 dark:border-gray-800 shadow-md mb-8">
            <CardContent className="py-12 px-6 text-center space-y-6">
              <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400 rounded-2xl flex items-center justify-center mx-auto shadow-inner animate-pulse">
                <ImageIcon className="w-8 h-8 animate-spin" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {stage === "uploading" ? "Uploading Images" : "Creating Your PDF"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{statusMessage}</p>
              </div>

              <div className="max-w-md mx-auto space-y-2">
                <div className="w-full bg-gray-200 dark:bg-gray-800 h-3 rounded-full overflow-hidden shadow-inner">
                  <div
                    className="bg-gradient-to-r from-orange-500 to-amber-500 h-full transition-all duration-300 ease-out rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 font-medium px-1">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* MAIN UPLOAD & WORKSPACE AREA */}
        {stage !== "completed" && stage !== "uploading" && stage !== "processing" && (
          <div className="space-y-8">
            {/* Multi-image dropzone */}
            <div
              onDragOver={handleZoneDragOver}
              onDragLeave={handleZoneDragLeave}
              onDrop={handleZoneDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
                isDragging
                  ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 scale-[0.99]"
                  : "border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-orange-400 hover:bg-orange-50/20 dark:hover:bg-orange-950/10"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".jpg,.jpeg,image/jpeg"
                className="hidden"
                aria-label="Upload JPG images to convert to PDF"
                onChange={(e) => {
                  if (e.target.files) addFiles(e.target.files);
                }}
              />
              <div className="w-16 h-16 rounded-2xl bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400 flex items-center justify-center mx-auto mb-4 shadow-sm">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                {images.length === 0
                  ? "Select or drop JPG images here"
                  : "Drop additional JPG images to add"}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-4">
                Upload up to {MAX_FILES} JPG/JPEG images (up to {MAX_FILE_SIZE_MB} MB each).
                Drag-and-drop to reorder images into your exact desired page sequence.
              </p>
              <Button
                type="button"
                variant="outline"
                className="border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-300 hover:bg-orange-50 dark:hover:bg-orange-950/30"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Browse JPG Images
              </Button>
            </div>

            {/* Selected Images Gallery & Reordering */}
            {images.length > 0 && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-200 dark:border-gray-800 pb-3">
                  <div>
                    <h2 className="text-lg font-bold flex items-center gap-2">
                      <Layers className="w-5 h-5 text-orange-500" />
                      Images to Convert ({images.length})
                    </h2>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Drag image cards or use arrow buttons to arrange pages in your requested order.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={clearAll}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 text-xs"
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1" />
                      Clear All
                    </Button>
                  </div>
                </div>

                {/* Grid of image cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {images.map((img, idx) => (
                    <div
                      key={img.id}
                      draggable
                      onDragStart={(e) => handleCardDragStart(e, idx)}
                      onDragOver={(e) => handleCardDragOver(e, idx)}
                      onDrop={(e) => handleCardDrop(e, idx)}
                      onDragEnd={handleCardDragEnd}
                      className={`group relative rounded-xl border bg-white dark:bg-gray-900 overflow-hidden shadow-sm transition-all duration-150 flex flex-col ${
                        draggedIndex === idx
                          ? "opacity-40 scale-95 border-orange-500"
                          : dragOverIndex === idx
                          ? "border-orange-500 ring-2 ring-orange-400/50 scale-[1.02]"
                          : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md"
                      }`}
                    >
                      {/* Top Header with Page Badge and Delete */}
                      <div className="absolute top-2 left-2 right-2 flex items-center justify-between z-10 pointer-events-none">
                        <span className="px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-sm text-white text-xs font-bold pointer-events-auto shadow">
                          #{idx + 1}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeImage(img.id);
                          }}
                          className="w-7 h-7 rounded-full bg-red-600/90 text-white flex items-center justify-center opacity-80 hover:opacity-100 hover:bg-red-700 transition pointer-events-auto shadow"
                          title="Remove image"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Image Preview Thumbnail */}
                      <div className="w-full h-36 bg-gray-100 dark:bg-gray-950 flex items-center justify-center overflow-hidden cursor-grab active:cursor-grabbing p-1">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={img.previewUrl}
                          alt={img.name}
                          className="max-h-full max-w-full object-contain rounded"
                        />
                      </div>

                      {/* Info & Reorder Controls */}
                      <div className="p-2.5 border-t border-gray-100 dark:border-gray-800/80 bg-gray-50/50 dark:bg-gray-900/50 flex-1 flex flex-col justify-between gap-1.5">
                        <div>
                          <p
                            className="text-xs font-semibold truncate text-gray-800 dark:text-gray-200"
                            title={img.name}
                          >
                            {img.name}
                          </p>
                          <div className="text-[11px] text-gray-500 flex items-center justify-between mt-0.5">
                            <span>{formatBytes(img.size)}</span>
                            {img.width && img.height && (
                              <span>
                                {img.width}x{img.height}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Reordering Buttons */}
                        <div className="flex items-center justify-between pt-1 border-t border-gray-200/60 dark:border-gray-800">
                          <button
                            type="button"
                            disabled={idx === 0}
                            onClick={() => moveImage(idx, idx - 1)}
                            className="p-1 rounded text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200/70 dark:hover:bg-gray-800 disabled:opacity-30 disabled:pointer-events-none transition"
                            title="Move earlier"
                          >
                            <ArrowUp className="w-3.5 h-3.5" />
                          </button>
                          <span className="text-[10px] text-gray-400 font-medium flex items-center gap-0.5">
                            <GripVertical className="w-3 h-3" />
                            Drag
                          </span>
                          <button
                            type="button"
                            disabled={idx === images.length - 1}
                            onClick={() => moveImage(idx, idx + 1)}
                            className="p-1 rounded text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200/70 dark:hover:bg-gray-800 disabled:opacity-30 disabled:pointer-events-none transition"
                            title="Move later"
                          >
                            <ArrowDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Configuration Options Card */}
                <Card className="border-gray-200 dark:border-gray-800 shadow-sm mt-8">
                  <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-orange-500" />
                      Page Layout & Margins
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Customize how your photos fit onto PDF pages.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-5 space-y-6">
                    {/* Orientation Selector */}
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-2">
                        Page Orientation
                      </label>
                      <div className="grid grid-cols-3 gap-2 sm:gap-3 max-w-lg">
                        <button
                          type="button"
                          onClick={() => setOrientation("auto")}
                          className={`p-3 rounded-xl border text-left transition ${
                            orientation === "auto"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Automatic</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">
                            Match image ratio
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setOrientation("portrait")}
                          className={`p-3 rounded-xl border text-left transition ${
                            orientation === "portrait"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Portrait</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">Vertical pages</div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setOrientation("landscape")}
                          className={`p-3 rounded-xl border text-left transition ${
                            orientation === "landscape"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Landscape</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">Horizontal pages</div>
                        </button>
                      </div>
                    </div>

                    {/* Page Size Selector */}
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-2">
                        Page Size
                      </label>
                      <div className="grid grid-cols-3 gap-2 sm:gap-3 max-w-lg">
                        <button
                          type="button"
                          onClick={() => setPageSize("fit")}
                          className={`p-3 rounded-xl border text-left transition ${
                            pageSize === "fit"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Fit to Image</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">
                            Exact photo dimensions
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setPageSize("a4")}
                          className={`p-3 rounded-xl border text-left transition ${
                            pageSize === "a4"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">A4</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">210 x 297 mm</div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setPageSize("letter")}
                          className={`p-3 rounded-xl border text-left transition ${
                            pageSize === "letter"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">US Letter</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">8.5 x 11 inches</div>
                        </button>
                      </div>
                    </div>

                    {/* Margins Selector */}
                    <div>
                      <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-2">
                        Margins
                      </label>
                      <div className="grid grid-cols-3 gap-2 sm:gap-3 max-w-lg">
                        <button
                          type="button"
                          onClick={() => setMargin("none")}
                          className={`p-3 rounded-xl border text-left transition ${
                            margin === "none"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">No Margin</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">Edge-to-edge</div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setMargin("small")}
                          className={`p-3 rounded-xl border text-left transition ${
                            margin === "small"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Small Margin</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">0.25 inch padding</div>
                        </button>
                        <button
                          type="button"
                          onClick={() => setMargin("normal")}
                          className={`p-3 rounded-xl border text-left transition ${
                            margin === "normal"
                              ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20 text-orange-950 dark:text-orange-200 font-semibold ring-1 ring-orange-500"
                              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="text-sm font-medium">Normal Margin</div>
                          <div className="text-[11px] text-gray-500 mt-0.5">0.50 inch padding</div>
                        </button>
                      </div>
                    </div>

                    {/* Output Filename */}
                    <div className="max-w-md">
                      <label
                        htmlFor="outputFilename"
                        className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 block mb-1.5"
                      >
                        Output PDF Name (Optional)
                      </label>
                      <input
                        id="outputFilename"
                        type="text"
                        placeholder="converted_images.pdf"
                        value={outputFilename}
                        onChange={(e) => setOutputFilename(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Convert Action Bar */}
                <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                    <Info className="w-4 h-4 text-orange-500" />
                    <span>
                      {images.length} {images.length === 1 ? "page" : "pages"} will be generated in
                      the exact order displayed above.
                    </span>
                  </div>
                  <Button
                    onClick={handleConvert}
                    size="lg"
                    className="w-full sm:w-auto bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-700 hover:to-amber-700 text-white font-bold px-8 shadow-lg shadow-orange-600/25 transition-all"
                  >
                    Convert to PDF
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* SEO, How-To, FAQs and Related Tools */}
        <ToolSeoSection tool={getToolSeoData("jpg-to-pdf")!} />
      </main>
    </div>
  );
}
