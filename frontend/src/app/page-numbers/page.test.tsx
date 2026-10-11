import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PageNumbersPdfPage from "./page";

describe("Add Page Numbers PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<PageNumbersPdfPage />);
    expect(screen.getByRole("heading", { name: "Add Page Numbers to PDF" })).toBeInTheDocument();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Choose PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info and settings", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "sample_report.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("sample_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page Number Settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add Page Numbers to PDF/i })).toBeInTheDocument();
  });

  it("allows selecting different position options", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const posBottomCenter = document.getElementById("pos-bottom_center-btn");
    const posTopRight = document.getElementById("pos-top_right-btn");
    const posTopLeft = document.getElementById("pos-top_left-btn");

    expect(posBottomCenter).toHaveClass("border-indigo-600");

    fireEvent.click(posTopRight!);
    expect(posTopRight).toHaveClass("border-indigo-600");

    fireEvent.click(posTopLeft!);
    expect(posTopLeft).toHaveClass("border-indigo-600");
  });

  it("allows selecting different numbering format options", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const fmtPageNTotal = document.getElementById("format-page_n_of_total-btn");
    const fmtPageN = document.getElementById("format-page_n-btn");
    const fmtN = document.getElementById("format-n-btn");

    expect(fmtPageNTotal).toHaveClass("border-indigo-600");

    fireEvent.click(fmtPageN!);
    expect(fmtPageN).toHaveClass("border-indigo-600");

    fireEvent.click(fmtN!);
    expect(fmtN).toHaveClass("border-indigo-600");
  });

  it("allows configuring start page and start number", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const startPageInput = document.getElementById("start-page-input") as HTMLInputElement;
    const startNumInput = document.getElementById("start-number-input") as HTMLInputElement;

    expect(startPageInput.value).toBe("1");
    expect(startNumInput.value).toBe("1");

    fireEvent.change(startPageInput, { target: { value: "3" } });
    expect(startPageInput.value).toBe("3");

    fireEvent.change(startNumInput, { target: { value: "10" } });
    expect(startNumInput.value).toBe("10");
  });

  it("rejects non-PDF files with an error message", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const docxFile = new File(["fake docx"], "notes.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    fireEvent.change(fileInput, { target: { files: [docxFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.docx/i)).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<PageNumbersPdfPage />);
    const fileInput = document.getElementById("page-numbers-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_test.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("clear_test.pdf")).toBeNull();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
  });
});
