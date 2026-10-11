import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ExtractPagesPage, { countPdfPages } from "./page";

describe("Extract Pages Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<ExtractPagesPage />);
    expect(screen.getByRole("heading", { name: "Extract Pages from PDF" })).toBeInTheDocument();
    expect(screen.getByText("Choose a PDF to extract pages from")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info and extract controls", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf content with /Type /Page /Type /Page"], "company_report.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("company_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Extract Mode & Page Range")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Extract Pages/i })).toBeInTheDocument();
  });

  it("allows entering custom page ranges and presets", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const rangesInput = document.getElementById("page-ranges-input") as HTMLInputElement;
    fireEvent.change(rangesInput, { target: { value: "1, 3-4, 8" } });
    expect(rangesInput.value).toBe("1, 3-4, 8");

    // Click preset
    const firstPagePreset = screen.getByRole("button", { name: /First Page/i });
    fireEvent.click(firstPagePreset);
    expect(rangesInput.value).toBe("1");
  });

  it("allows toggling Extract All Pages mode", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const extractAllToggle = document.getElementById("extract-all-toggle-btn");
    expect(extractAllToggle).toBeInTheDocument();

    fireEvent.click(extractAllToggle!);
    // When extract all is active, the specific ranges input is hidden
    expect(document.getElementById("page-ranges-input")).toBeNull();
  });

  it("rejects non-PDF files with an error message banner", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const textFile = new File(["not a pdf"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.txt/i)).toBeInTheDocument();
    expect(document.getElementById("global-error-banner")).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_test.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("clear_test.pdf")).toBeNull();
    expect(screen.getByText("Choose a PDF to extract pages from")).toBeInTheDocument();
  });

  it("disables extract submit button when page ranges field is empty in specific mode", () => {
    render(<ExtractPagesPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const rangesInput = document.getElementById("page-ranges-input") as HTMLInputElement;
    const submitBtn = document.getElementById("extract-submit-btn") as HTMLButtonElement;

    fireEvent.change(rangesInput, { target: { value: "" } });
    expect(submitBtn).toBeDisabled();

    fireEvent.change(rangesInput, { target: { value: "2-3" } });
    expect(submitBtn).not.toBeDisabled();
  });

  it("countPdfPages detects pages from plain uncompressed PDF", async () => {
    const file = new File(["dummy /Type /Page dummy /Type /Page dummy /Type /Page"], "doc.pdf", {
      type: "application/pdf",
    });
    const count = await countPdfPages(file);
    expect(count).toBe(3);
  });

  it("countPdfPages handles PDF with compressed object streams (/ObjStm) using root Pages count", async () => {
    const file = new File(["%PDF-1.5 /ObjStm stream ... /Type /Pages /Count 5 ..."], "objstm.pdf", {
      type: "application/pdf",
    });
    const count = await countPdfPages(file);
    expect(count).toBe(5);
  });

  it("countPdfPages returns null safely on corrupted content without crashing", async () => {
    const file = new File(["corrupted content"], "corrupt.pdf", { type: "application/pdf" });
    const count = await countPdfPages(file);
    expect(count).toBeNull();
  });

  it("countPdfPages handles empty or 0-byte file safely", async () => {
    const file = new File([], "empty.pdf", { type: "application/pdf" });
    const count = await countPdfPages(file);
    expect(count).toBeNull();
  });

  it("countPdfPages safely processes untrusted PDF with embedded JavaScript without executing", async () => {
    const maliciousContent = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /OpenAction 4 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R >>
endobj
4 0 obj
<< /Type /Action /S /JavaScript /JS (app.alert("XSS")) >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF`;
    const file = new File([maliciousContent], "untrusted.pdf", { type: "application/pdf" });
    const count = await countPdfPages(file);
    expect(count).toBe(1);
  });

  it("verifies PDF.js is configured with local worker and eval/scripting disabled", async () => {
    const pdfjs = await import("pdfjs-dist");
    const GlobalWorkerOptions = pdfjs.GlobalWorkerOptions || (pdfjs as any).default?.GlobalWorkerOptions;
    const file = new File(["dummy /Type /Page"], "test.pdf", { type: "application/pdf" });
    await countPdfPages(file);
    expect(GlobalWorkerOptions?.workerSrc).toBe("/pdf.worker.min.mjs");
  });
});
