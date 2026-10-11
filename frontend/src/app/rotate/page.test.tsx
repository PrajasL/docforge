import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RotatePdfPage from "./page";

describe("Rotate PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<RotatePdfPage />);
    expect(screen.getByRole("heading", { name: "Rotate PDF Pages Permanently" })).toBeInTheDocument();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Choose PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info and rotation settings", () => {
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "sample_document.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("sample_document.pdf")).toBeInTheDocument();
    expect(screen.getByText("Rotation Settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Rotate PDF Now/i })).toBeInTheDocument();
  });

  it("renders rotation angle options: 90°, 180°, and 270°", () => {
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("90° Right")).toBeInTheDocument();
    expect(screen.getByText("180° Flip")).toBeInTheDocument();
    expect(screen.getByText("270° Left")).toBeInTheDocument();
  });

  it("allows switching between rotation angles", () => {
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const btn90 = document.getElementById("angle-90-btn");
    const btn180 = document.getElementById("angle-180-btn");
    const btn270 = document.getElementById("angle-270-btn");

    expect(btn90).toHaveClass("border-teal-600");

    fireEvent.click(btn180!);
    expect(btn180).toHaveClass("border-teal-600");

    fireEvent.click(btn270!);
    expect(btn270).toHaveClass("border-teal-600");
  });

  it("allows switching between all pages and custom pages scope", () => {
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

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
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const docxFile = new File(["fake docx"], "document.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    fireEvent.change(fileInput, { target: { files: [docxFile] } });

    expect(screen.getByText(/Skipped non-PDF file: document.docx/i)).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<RotatePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_me.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_me.pdf")).toBeInTheDocument();

    const removeBtn = screen.getByTitle("Remove file");
    fireEvent.click(removeBtn);

    expect(screen.queryByText("clear_me.pdf")).toBeNull();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
  });
});
