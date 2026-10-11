import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { useJobProgress, trackJobUntilDone } from "./use-job-progress";

describe("useJobProgress hook", () => {
  let mockEventSourceInstances: any[] = [];

  class MockEventSource {
    url: string;
    onopen: any = null;
    onmessage: any = null;
    onerror: any = null;
    listeners: Record<string, any[]> = {};

    constructor(url: string) {
      this.url = url;
      mockEventSourceInstances.push(this);
    }

    addEventListener(event: string, callback: any) {
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(callback);
    }

    emit(event: string, data: any) {
      const msgEvent = { data: JSON.stringify(data) };
      if (this.listeners[event]) {
        this.listeners[event].forEach((cb) => cb(msgEvent));
      }
      if (this.onmessage) {
        this.onmessage(msgEvent);
      }
    }

    close = vi.fn();
  }

  beforeEach(() => {
    mockEventSourceInstances = [];
    // @ts-expect-error Mocking EventSource
    globalThis.EventSource = MockEventSource;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("subscribes to SSE stream and handles progress updates", () => {
    const onProgress = vi.fn();
    const onCompleted = vi.fn();

    const { result } = renderHook(() =>
      useJobProgress("job-123", { onProgress, onCompleted })
    );

    expect(mockEventSourceInstances.length).toBe(1);
    const es = mockEventSourceInstances[0];
    expect(es.url).toContain("/api/v1/jobs/job-123/progress");

    // Open connection
    act(() => {
      es.onopen?.();
    });
    expect(result.current.isUsingSse).toBe(true);

    // Receive progress update
    act(() => {
      es.emit("progress", { job_id: "job-123", status: "processing", progress: 45 });
    });

    expect(result.current.progress).toBe(45);
    expect(result.current.status).toBe("processing");
    expect(onProgress).toHaveBeenCalledWith(45, "processing");

    // Receive terminal completion
    act(() => {
      es.emit("progress", {
        job_id: "job-123",
        status: "completed",
        progress: 100,
        result_file: { original_name: "output.pdf" },
      });
    });

    expect(result.current.progress).toBe(100);
    expect(result.current.status).toBe("completed");
    expect(result.current.isFinished).toBe(true);
    expect(onCompleted).toHaveBeenCalled();
    expect(es.close).toHaveBeenCalled();
  });

  it("handles failure update and closes SSE stream", () => {
    const onFailed = vi.fn();

    const { result } = renderHook(() =>
      useJobProgress("job-failed-456", { onFailed })
    );

    const es = mockEventSourceInstances[0];

    act(() => {
      es.emit("progress", {
        job_id: "job-failed-456",
        status: "failed",
        progress: 20,
        error_message: "Corrupted structure",
      });
    });

    expect(result.current.status).toBe("failed");
    expect(result.current.errorMessage).toBe("Corrupted structure");
    expect(onFailed).toHaveBeenCalled();
    expect(es.close).toHaveBeenCalled();
  });

  it("falls back to HTTP polling when SSE encounters an error", async () => {
    // Mock fetch for polling fallback
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        data: {
          job: {
            id: "job-789",
            status: "PROCESSING",
            progress: 80,
          },
        },
      }),
    });
    globalThis.fetch = fetchMock;

    const { result } = renderHook(() => useJobProgress("job-789"));

    const es = mockEventSourceInstances[0];

    // Trigger SSE error
    act(() => {
      es.onerror?.(new Event("error"));
    });

    expect(es.close).toHaveBeenCalled();
    expect(result.current.isUsingSse).toBe(false);

    // Fast-forward interval timer to trigger polling
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/jobs/job-789"),
      expect.any(Object)
    );
  });

  it("enforces monotonic progress when out-of-order updates arrive", () => {
    const onProgress = vi.fn();
    const { result } = renderHook(() =>
      useJobProgress("job-monotonic-1", { onProgress })
    );

    const es = mockEventSourceInstances[0];

    act(() => {
      es.emit("progress", { job_id: "job-monotonic-1", status: "processing", progress: 40 });
    });
    expect(result.current.progress).toBe(40);
    expect(onProgress).toHaveBeenLastCalledWith(40, "processing");

    // Out-of-order regressing progress (30 should be ignored / clamped to 40)
    act(() => {
      es.emit("progress", { job_id: "job-monotonic-1", status: "processing", progress: 30 });
    });
    expect(result.current.progress).toBe(40);
    expect(onProgress).toHaveBeenLastCalledWith(40, "processing");

    // Advancing progress
    act(() => {
      es.emit("progress", { job_id: "job-monotonic-1", status: "processing", progress: 75 });
    });
    expect(result.current.progress).toBe(75);
    expect(onProgress).toHaveBeenLastCalledWith(75, "processing");
  });

  it("resets state and reconnects when jobId changes", () => {
    const { result, rerender } = renderHook(
      ({ id }) => useJobProgress(id),
      { initialProps: { id: "job-a" } }
    );

    const esA = mockEventSourceInstances[0];
    act(() => {
      esA.emit("progress", { job_id: "job-a", status: "processing", progress: 50 });
    });
    expect(result.current.progress).toBe(50);

    // Change jobId
    rerender({ id: "job-b" });
    expect(esA.close).toHaveBeenCalled();
    expect(mockEventSourceInstances.length).toBe(2);
    expect(result.current.progress).toBe(0);
    expect(result.current.status).toBe("idle");
  });

  it("trackJobUntilDone resolves on completed SSE event", async () => {
    const promise = trackJobUntilDone("job-track-1", "http://localhost:8000");

    const es = mockEventSourceInstances[mockEventSourceInstances.length - 1];

    act(() => {
      es.emit("progress", {
        job_id: "job-track-1",
        status: "completed",
        progress: 100,
        result_file: { name: "done.pdf" },
      });
    });

    const res = await promise;
    expect(res.status).toBe("completed");
    expect(res.progress).toBe(100);
    expect(es.close).toHaveBeenCalled();
  });
});
