import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import WatermarkPdfPage from "./page";

describe("Watermark PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<WatermarkPdfPage />);
    expect(screen.getByRole("heading", { name: "Add Text Watermark to PDF" })).toBeInTheDocument();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Choose PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info and watermark settings", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "invoice_sample.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("invoice_sample.pdf")).toBeInTheDocument();
    expect(screen.getByText("Watermark Settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add Watermark to PDF/i })).toBeInTheDocument();
  });

  it("allows modifying watermark text", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const textInput = document.getElementById("watermark-text-input") as HTMLInputElement;
    expect(textInput.value).toBe("CONFIDENTIAL");

    fireEvent.change(textInput, { target: { value: "SAMPLE DRAFT" } });
    expect(textInput.value).toBe("SAMPLE DRAFT");
  });

  it("renders and switches position presets", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const diagBtn = document.getElementById("pos-diagonal-btn");
    const centerBtn = document.getElementById("pos-center-btn");
    const topBtn = document.getElementById("pos-top-btn");
    const bottomBtn = document.getElementById("pos-bottom-btn");

    expect(diagBtn).toHaveClass("border-indigo-600");

    fireEvent.click(centerBtn!);
    expect(centerBtn).toHaveClass("border-indigo-600");

    fireEvent.click(topBtn!);
    expect(topBtn).toHaveClass("border-indigo-600");

    fireEvent.click(bottomBtn!);
    expect(bottomBtn).toHaveClass("border-indigo-600");
  });

  it("allows switching between all pages and custom pages scope", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const scopeCustomBtn = document.getElementById("scope-custom-btn");
    expect(document.getElementById("custom-pages-input")).toBeNull();

    fireEvent.click(scopeCustomBtn!);
    const customPagesInput = document.getElementById("custom-pages-input") as HTMLInputElement;
    expect(customPagesInput).not.toBeNull();

    fireEvent.change(customPagesInput, { target: { value: "1, 3-5" } });
    expect(customPagesInput.value).toBe("1, 3-5");
  });

  it("rejects non-PDF files with an error message", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const docxFile = new File(["fake docx"], "report.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    fireEvent.change(fileInput, { target: { files: [docxFile] } });

    expect(screen.getByText(/Skipped non-PDF file: report.docx/i)).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<WatermarkPdfPage />);
    const fileInput = document.getElementById("watermark-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_watermark.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_watermark.pdf")).toBeInTheDocument();

    const removeBtn = screen.getByTitle("Remove file");
    fireEvent.click(removeBtn);

    expect(screen.queryByText("clear_watermark.pdf")).toBeNull();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
  });
});
