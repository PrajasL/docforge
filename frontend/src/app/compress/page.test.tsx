import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CompressPdfPage from "./page";

describe("Compress PDF Page", () => {
  it("renders page heading, description, and file dropzone", () => {
    render(<CompressPdfPage />);
    expect(screen.getByRole("heading", { name: "Compress PDF Document" })).toBeInTheDocument();
    expect(
      screen.getByText("Choose a PDF file or drag & drop it here")
    ).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays selected file card", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "large_report.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("large_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Selected Document")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Compress PDF/i })).toBeInTheDocument();
  });

  it("renders all three compression tiers: Recommended, Balanced, Maximum", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("Recommended")).toBeInTheDocument();
    expect(screen.getByText("Standard Compression")).toBeInTheDocument();
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.getByText("Strong Compression")).toBeInTheDocument();
    expect(screen.getByText("Maximum")).toBeInTheDocument();
    expect(screen.getByText("Extreme Compression")).toBeInTheDocument();
  });

  it("allows switching between compression tiers", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Click Balanced
    const balancedBtn = screen.getByText("Balanced").closest("button");
    expect(balancedBtn).not.toBeNull();
    fireEvent.click(balancedBtn!);
    expect(balancedBtn).toHaveClass("border-emerald-600");

    // Click Maximum
    const maxBtn = screen.getByText("Maximum").closest("button");
    expect(maxBtn).not.toBeNull();
    fireEvent.click(maxBtn!);
    expect(maxBtn).toHaveClass("border-emerald-600");

    // Click Recommended
    const recBtn = screen.getByText("Recommended").closest("button");
    expect(recBtn).not.toBeNull();
    fireEvent.click(recBtn!);
    expect(recBtn).toHaveClass("border-emerald-600");
  });

  it("displays explanatory notice about image compression and quality", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(
      screen.getByText(/Stronger compression reduces image resolution and applies lossy JPEG encoding/i)
    ).toBeInTheDocument();
  });

  it("rejects non-PDF files with an error banner", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const docxFile = new File(["fake docx"], "presentation.pptx", { type: "application/vnd.ms-powerpoint" });
    fireEvent.change(fileInput, { target: { files: [docxFile] } });

    expect(screen.getByText(/Skipped non-PDF file: presentation.pptx/i)).toBeInTheDocument();
  });

  it("allows removing selected file using Change File button", () => {
    render(<CompressPdfPage />);
    const fileInput = document.getElementById("compress-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "doc_to_clear.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("doc_to_clear.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("doc_to_clear.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("Choose a PDF file or drag & drop it here")).toBeInTheDocument();
  });
});
