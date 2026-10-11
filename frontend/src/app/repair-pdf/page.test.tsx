import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RepairPdfPage from "./page";

// Mock ToolHeader and ToolSeoSection to keep tests focused
vi.mock("@/components/tool-header", () => ({
  ToolHeader: ({ toolName }: { toolName: string }) => (
    <div data-testid="tool-header">{toolName}</div>
  ),
}));

vi.mock("@/components/tool-seo-section", () => ({
  ToolSeoSection: ({ tool }: { tool: any }) => (
    <div data-testid="tool-seo-section">{tool.h1}</div>
  ),
}));

describe("Repair PDF Page (/repair-pdf)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("renders page heading, description, dropzone, and SEO section", () => {
    render(<RepairPdfPage />);
    expect(screen.getByText("Repair Corrupted PDF Document")).toBeInTheDocument();
    expect(screen.getByText(/Safely reconstruct damaged cross-reference tables/i)).toBeInTheDocument();
    expect(screen.getByText("Choose a PDF file or drag & drop it here")).toBeInTheDocument();
    expect(screen.getByTestId("tool-header")).toHaveTextContent("Repair PDF");
    expect(screen.getByTestId("tool-seo-section")).toHaveTextContent("Repair Corrupted PDF Files");
  });

  it("rejects non-PDF files with clear error message", () => {
    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const textFile = new File(["dummy text content"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByRole("alert")).toHaveTextContent("Skipped non-PDF file: notes.txt. Only PDF files are supported.");
  });

  it("handles adding a PDF file and displays selected file card with safe repair notice", () => {
    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const samplePdf = new File([new ArrayBuffer(1024 * 50)], "damaged_contract.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [samplePdf] } });

    expect(screen.getByTestId("selected-file-item")).toBeInTheDocument();
    expect(screen.getByText("damaged_contract.pdf")).toBeInTheDocument();
    expect(screen.getByText("50 KB")).toBeInTheDocument();
    expect(screen.getByText(/Safe, Non-Destructive Repair/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Repair PDF/i })).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const samplePdf = new File([new ArrayBuffer(2048)], "corrupt.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [samplePdf] } });

    expect(screen.getByText("corrupt.pdf")).toBeInTheDocument();
    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByTestId("selected-file-item")).not.toBeInTheDocument();
    expect(screen.getByText("Choose a PDF file or drag & drop it here")).toBeInTheDocument();
  });

  it("allows customizing the output filename", () => {
    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const samplePdf = new File([new ArrayBuffer(2048)], "broken_invoice.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [samplePdf] } });

    const nameInput = document.getElementById("output-filename-input") as HTMLInputElement;
    expect(nameInput.value).toBe("repaired_broken_invoice.pdf");

    fireEvent.change(nameInput, { target: { value: "salvaged_invoice_v2.pdf" } });
    expect(nameInput.value).toBe("salvaged_invoice_v2.pdf");
  });

  it("executes repair workflow and displays completed state with repaired badge", async () => {
    const fetchMock = vi.fn();
    // 1. Create job
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        data: {
          job: { id: "job_repair_123" },
          uploads: [{ upload_url: "http://storage/upload", file_id: "fid_123", upload_method: "PUT" }],
        },
      }),
    });
    // 2. Upload bytes
    fetchMock.mockResolvedValueOnce({ ok: true });
    // 3. Start job
    fetchMock.mockResolvedValueOnce({ ok: true });
    // 4. Poll status -> COMPLETED
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        data: {
          job: {
            id: "job_repair_123",
            status: "COMPLETED",
            result_file: {
              id: "res_123",
              original_name: "repaired_broken.pdf",
              size_bytes: 4500,
              page_count: 3,
              repaired: true,
              repair_action: "XREF_RECONSTRUCTED",
              status_detail: "Reconstructed damaged cross-reference tables and recovered 3 page(s).",
            },
          },
        },
      }),
    });

    global.fetch = fetchMock;

    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const samplePdf = new File([new ArrayBuffer(4000)], "broken.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [samplePdf] } });

    const repairBtn = screen.getByRole("button", { name: /Repair PDF/i });
    fireEvent.click(repairBtn);

    await waitFor(() => {
      expect(screen.getByText("PDF Successfully Repaired!")).toBeInTheDocument();
      expect(screen.getByText("Structural Damage Repaired")).toBeInTheDocument();
      expect(screen.getByText(/3 page\(s\) recovered/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Download Repaired PDF/i })).toBeInTheDocument();
    });
  });

  it("handles unrecoverable file error gracefully", async () => {
    const fetchMock = vi.fn();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        data: {
          job: { id: "job_repair_fail" },
          uploads: [{ upload_url: "http://storage/upload", file_id: "fid_fail", upload_method: "PUT" }],
        },
      }),
    });
    // Upload bytes
    fetchMock.mockResolvedValueOnce({ ok: true });
    // Start job
    fetchMock.mockResolvedValueOnce({ ok: true });
    // Poll status -> FAILED
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        data: {
          job: {
            id: "job_repair_fail",
            status: "FAILED",
            error_code: "UNRECOVERABLE_PDF",
            error_message: "File 'garbage.pdf' is severely corrupted and could not be structurally recovered.",
          },
        },
      }),
    });

    global.fetch = fetchMock;

    render(<RepairPdfPage />);
    const fileInput = document.getElementById("repair-file-input") as HTMLInputElement;

    const samplePdf = new File([new ArrayBuffer(100)], "garbage.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [samplePdf] } });

    const repairBtn = screen.getByRole("button", { name: /Repair PDF/i });
    fireEvent.click(repairBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("severely corrupted and could not be structurally recovered");
    });
  });
});
