"use client";

import { useEffect, useState, useRef, useCallback } from "react";

export interface JobProgressUpdate {
  job_id: string;
  status: string;
  progress: number;
  result_file?: Record<string, any>;
  error_message?: string;
  error_code?: string;
}

export interface UseJobProgressOptions {
  apiUrl?: string;
  sessionId?: string;
  pollIntervalMs?: number;
  onCompleted?: (result: JobProgressUpdate) => void;
  onFailed?: (error: JobProgressUpdate) => void;
  onProgress?: (progress: number, status: string) => void;
}

export function useJobProgress(
  jobId: string | null,
  options: UseJobProgressOptions = {}
) {
  const {
    apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    sessionId,
    pollIntervalMs = 1000,
    onCompleted,
    onFailed,
    onProgress,
  } = options;

  const [status, setStatus] = useState<string>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [resultFile, setResultFile] = useState<Record<string, any> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUsingSse, setIsUsingSse] = useState<boolean>(false);
  const [isFinished, setIsFinished] = useState<boolean>(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasFinishedRef = useRef<boolean>(false);
  const lastProgressRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const handleUpdate = useCallback(
    (data: JobProgressUpdate) => {
      const normalizedStatus = (data.status || "").toLowerCase();
      const rawProgress = data.progress ?? 0;
      const monotonicProgress =
        normalizedStatus === "completed"
          ? 100
          : normalizedStatus === "processing"
          ? Math.max(lastProgressRef.current, rawProgress)
          : rawProgress;

      lastProgressRef.current = monotonicProgress;
      setStatus(normalizedStatus);
      setProgress(monotonicProgress);

      if (onProgress) {
        onProgress(monotonicProgress, normalizedStatus);
      }

      if (data.error_message) {
        setErrorMessage(data.error_message);
      }

      if (data.result_file) {
        setResultFile(data.result_file);
      }

      if (
        normalizedStatus === "completed" ||
        normalizedStatus === "failed" ||
        normalizedStatus === "cancelled"
      ) {
        hasFinishedRef.current = true;
        setIsFinished(true);
        cleanup();

        if (normalizedStatus === "completed" && onCompleted) {
          onCompleted(data);
        } else if (normalizedStatus === "failed" && onFailed) {
          onFailed(data);
        }
      }
    },
    [cleanup, onCompleted, onFailed, onProgress]
  );

  // Fallback HTTP polling mechanism
  const startPolling = useCallback(() => {
    if (hasFinishedRef.current || pollTimerRef.current || !jobId) return;

    setIsUsingSse(false);

    const poll = async () => {
      if (hasFinishedRef.current) return;
      try {
        const headers: Record<string, string> = {};
        if (sessionId) headers["X-Session-Id"] = sessionId;

        const res = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, { headers });
        if (!res.ok) return;

        const json = await res.json();
        const job = json?.data?.job;
        if (job) {
          handleUpdate({
            job_id: job.id,
            status: job.status,
            progress: job.progress,
            result_file: job.result_file,
            error_message: job.error_message,
            error_code: job.error_code,
          });
        }
      } catch {
        // Retry on next interval
      }
    };

    // Immediate first poll
    poll();
    pollTimerRef.current = setInterval(poll, pollIntervalMs);
  }, [apiUrl, jobId, sessionId, pollIntervalMs, handleUpdate]);

  useEffect(() => {
    if (!jobId) {
      cleanup();
      return;
    }

    hasFinishedRef.current = false;
    lastProgressRef.current = 0;
    setStatus("idle");
    setProgress(0);
    setIsFinished(false);
    setErrorMessage(null);
    setResultFile(null);

    // Attempt Server-Sent Events first
    if (typeof window !== "undefined" && "EventSource" in window) {
      const sseUrl = `${apiUrl}/api/v1/jobs/${jobId}/progress`;
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsUsingSse(true);
      };

      const onMessageHandler = (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data);
          handleUpdate(parsed);
        } catch {
          // Heartbeat or malformed comment
        }
      };

      es.addEventListener("progress", onMessageHandler);
      es.onmessage = onMessageHandler;

      es.onerror = () => {
        // SSE disconnected or dropped; switch seamlessly to HTTP polling
        if (!hasFinishedRef.current) {
          cleanup();
          startPolling();
        }
      };
    } else {
      // EventSource not supported in environment
      startPolling();
    }

    return () => {
      cleanup();
    };
  }, [jobId, apiUrl, cleanup, handleUpdate, startPolling]);

  return {
    status,
    progress,
    resultFile,
    errorMessage,
    isUsingSse,
    isFinished,
    cancel: cleanup,
  };
}

/**
 * Promise-based tracking helper that connects to SSE with automatic polling fallback.
 */
export async function trackJobUntilDone(
  jobId: string,
  apiUrl: string = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  sessionId?: string,
  onProgress?: (progress: number, status: string) => void
): Promise<Record<string, any>> {
  return new Promise((resolve, reject) => {
    let resolved = false;
    let pollInterval: NodeJS.Timeout | null = null;
    let es: EventSource | null = null;

    const finish = (result: Record<string, any>, isError = false) => {
      if (resolved) return;
      resolved = true;
      if (es) {
        es.close();
        es = null;
      }
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (isError) {
        reject(new Error(result.error_message || "Job processing failed"));
      } else {
        resolve(result);
      }
    };

    let lastProgress = 0;
    const processPayload = (payload: any) => {
      const s = String(payload.status || "").toLowerCase();
      let p = payload.progress ?? 0;
      if (s === "completed") {
        p = 100;
      } else if (s === "processing" && p < lastProgress) {
        p = lastProgress;
      }
      lastProgress = p;
      if (onProgress) onProgress(p, s);

      if (s === "completed") {
        finish({ ...payload, progress: p }, false);
      } else if (s === "failed" || s === "cancelled") {
        finish(payload, true);
      }
    };

    const startPollingFallback = () => {
      if (resolved || pollInterval) return;
      const poll = async () => {
        if (resolved) return;
        try {
          const headers: Record<string, string> = {};
          if (sessionId) headers["X-Session-Id"] = sessionId;
          const res = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, { credentials: "omit", headers });
          if (res.ok) {
            const json = await res.json();
            const job = json?.data?.job;
            if (job) {
              processPayload({
                job_id: job.id,
                status: job.status,
                progress: job.progress,
                result_file: job.result_file,
                error_message: job.error_message,
              });
            }
          }
        } catch {
          // Wait for next cycle
        }
      };
      poll();
      pollInterval = setInterval(poll, 1000);
    };

    if (typeof window !== "undefined" && "EventSource" in window) {
      try {
        es = new EventSource(`${apiUrl}/api/v1/jobs/${jobId}/progress`);
        const handler = (e: MessageEvent) => {
          try {
            processPayload(JSON.parse(e.data));
          } catch {}
        };
        es.addEventListener("progress", handler);
        es.onmessage = handler;
        es.onerror = () => {
          if (!resolved) {
            if (es) {
              es.close();
              es = null;
            }
            startPollingFallback();
          }
        };
      } catch {
        startPollingFallback();
      }
    } else {
      startPollingFallback();
    }
  });
}
