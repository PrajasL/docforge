import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PdfToJpgPage from "./page";

describe("PDF to JPG Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<PdfToJpgPage />);
    expect(screen.getByRole("heading", { name: "Convert PDF to JPG Images" })).toBeInTheDocument();
    expect(screen.getByText("Choose a PDF to convert to JPG")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info, settings, and submit button", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf content with /Type /Page /Type /Page"], "presentation.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("presentation.pdf")).toBeInTheDocument();
    expect(screen.getByText("Image Quality & Resolution")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Convert All Pages to JPG/i })).toBeInTheDocument();
  });

  it("allows switching resolution options between 150 DPI and 300 DPI", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const card150 = document.getElementById("dpi-150-card");
    const card300 = document.getElementById("dpi-300-card");

    expect(card150).toBeInTheDocument();
    expect(card300).toBeInTheDocument();

    // Click 300 DPI
    fireEvent.click(card300!);
    expect(card300).toHaveClass("border-amber-600");

    // Click 150 DPI
    fireEvent.click(card150!);
    expect(card150).toHaveClass("border-amber-600");
  });

  it("allows adjusting quality and editing custom output filename", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const q95Btn = document.getElementById("quality-95-btn") as HTMLButtonElement;
    fireEvent.click(q95Btn);
    expect(screen.getByText("95%")).toBeInTheDocument();

    const filenameInput = document.getElementById("output-filename-input") as HTMLInputElement;
    fireEvent.change(filenameInput, { target: { value: "my_custom_images.zip" } });
    expect(filenameInput.value).toBe("my_custom_images.zip");
  });

  it("rejects non-PDF files with error banner", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const textFile = new File(["plain text"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.txt/i)).toBeInTheDocument();
    expect(document.getElementById("global-error-banner")).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_test.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("clear_test.pdf")).toBeNull();
    expect(screen.getByText("Choose a PDF to convert to JPG")).toBeInTheDocument();
  });

  it("rejects oversized file uploads exceeding 50 MB", () => {
    render(<PdfToJpgPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const oversizedFile = new File(["huge file"], "huge_book.pdf", { type: "application/pdf" });
    Object.defineProperty(oversizedFile, "size", { value: 55 * 1024 * 1024 });
    fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

    expect(screen.getByText(/exceeds maximum allowed size of 50 MB/i)).toBeInTheDocument();
    expect(screen.queryByText("huge_book.pdf")).toBeNull();
  });
});

