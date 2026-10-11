import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SplitPdfPage from "./page";

describe("Split PDF Page", () => {
  it("renders page heading, description, and file dropzone", () => {
    render(<SplitPdfPage />);
    expect(screen.getByRole("heading", { name: "Split PDF Document" })).toBeInTheDocument();
    expect(
      screen.getByText("Choose a PDF file or drag & drop it here")
    ).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays selected file card", () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "sample_book.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("sample_book.pdf")).toBeInTheDocument();
    expect(screen.getByText("Selected Document")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Split PDF/i })).toBeInTheDocument();
  });

  it("toggles between 'Custom Page Ranges' and 'Extract Every Page' modes", () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "sample.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Initially in ranges mode
    expect(screen.getByLabelText(/Page Ranges/i)).toBeInTheDocument();

    // Click "Extract Every Page"
    const everyPageBtn = screen.getByText("Extract Every Page").closest("button");
    expect(everyPageBtn).not.toBeNull();
    fireEvent.click(everyPageBtn!);

    // Ranges input should no longer be rendered
    expect(screen.queryByLabelText(/Page Ranges/i)).not.toBeInTheDocument();

    // Click back to "Custom Page Ranges"
    const rangesBtn = screen.getByText("Custom Page Ranges").closest("button");
    expect(rangesBtn).not.toBeNull();
    fireEvent.click(rangesBtn!);

    expect(screen.getByLabelText(/Page Ranges/i)).toBeInTheDocument();
  });

  it("allows setting page ranges and clicking presets", () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const rangesInput = screen.getByLabelText(/Page Ranges/i) as HTMLInputElement;
    fireEvent.change(rangesInput, { target: { value: "1-4, 5-10" } });
    expect(rangesInput.value).toBe("1-4, 5-10");

    // Click quick preset "1, 2-3"
    const presetBtn = screen.getByRole("button", { name: "1, 2-3" });
    fireEvent.click(presetBtn);
    expect(rangesInput.value).toBe("1, 2-3");
  });

  it("shows an error when splitting with empty range", async () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const rangesInput = screen.getByLabelText(/Page Ranges/i) as HTMLInputElement;
    fireEvent.change(rangesInput, { target: { value: "" } });

    const splitBtn = screen.getByRole("button", { name: /Split PDF/i });
    fireEvent.click(splitBtn);

    expect(screen.getByText("Please specify at least one page range (e.g. '1-3, 4-6').")).toBeInTheDocument();
  });

  it("rejects non-PDF files with an error banner", () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const nonPdfFile = new File(["some text"], "report.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    fireEvent.change(fileInput, { target: { files: [nonPdfFile] } });

    expect(screen.getByText(/Skipped non-PDF file: report.docx/i)).toBeInTheDocument();
  });

  it("allows removing selected file using Change File button", () => {
    render(<SplitPdfPage />);
    const fileInput = document.getElementById("split-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "my_doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("my_doc.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("my_doc.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("Choose a PDF file or drag & drop it here")).toBeInTheDocument();
  });
});
