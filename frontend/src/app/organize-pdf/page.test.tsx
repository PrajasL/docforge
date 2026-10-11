import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import OrganizePdfPage from "./page";

describe("Organize PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<OrganizePdfPage />);
    expect(screen.getByRole("heading", { name: "Organize PDF" })).toBeInTheDocument();
    expect(screen.getByText("Visual page reordering, rotation, duplication, and deletion")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays page grid", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(
      ["dummy content with /Type /Page /Type /Page /Type /Page"],
      "test_doc.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("test_doc.pdf")).toBeInTheDocument();
      expect(document.getElementById("pages-grid")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Compile & Organize PDF/i })).toBeInTheDocument();
  });

  it("allows rotating an individual page (+90° increments)", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(
      ["dummy content with /Type /Page /Type /Page"],
      "rotate_test.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(document.getElementById("pages-grid")).toBeInTheDocument();
    });

    const rotateButtons = screen.getAllByTitle("Rotate +90° clockwise");
    expect(rotateButtons.length).toBeGreaterThan(0);

    // Rotate first page
    fireEvent.click(rotateButtons[0]);
    expect(screen.getByText("+90°")).toBeInTheDocument();

    // Rotate again -> +180°
    fireEvent.click(rotateButtons[0]);
    expect(screen.getByText("+180°")).toBeInTheDocument();
  });

  it("allows duplicating and deleting pages", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(
      ["dummy content with /Type /Page /Type /Page"],
      "dup_del_test.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(document.getElementById("pages-grid")).toBeInTheDocument();
    });

    // Duplicate first page
    const duplicateButtons = screen.getAllByTitle("Duplicate page");
    fireEvent.click(duplicateButtons[0]);

    // Should now have 3 pages
    await waitFor(() => {
      expect(screen.getAllByTitle("Duplicate page").length).toBe(3);
    });

    // Delete a page
    const deleteButtons = screen.getAllByTitle("Delete page");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getAllByTitle("Duplicate page").length).toBe(2);
    });
  });

  it("supports undo and reset to original pages", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(
      ["dummy content with /Type /Page /Type /Page"],
      "undo_test.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(document.getElementById("pages-grid")).toBeInTheDocument();
    });

    const undoBtn = document.getElementById("undo-btn") as HTMLButtonElement;
    expect(undoBtn).toBeDisabled();

    // Perform an edit: rotate first page
    const rotateButtons = screen.getAllByTitle("Rotate +90° clockwise");
    fireEvent.click(rotateButtons[0]);
    expect(screen.getByText("+90°")).toBeInTheDocument();
    expect(undoBtn).not.toBeDisabled();

    // Click Undo
    fireEvent.click(undoBtn);
    expect(screen.queryByText("+90°")).toBeNull();

    // Perform another edit and Reset
    fireEvent.click(rotateButtons[0]);
    expect(screen.getByText("+90°")).toBeInTheDocument();

    const resetBtn = document.getElementById("reset-btn") as HTMLButtonElement;
    fireEvent.click(resetBtn);
    expect(screen.queryByText("+90°")).toBeNull();
  });

  it("supports selection controls and batch actions", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(
      ["dummy content with /Type /Page /Type /Page /Type /Page"],
      "batch_test.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(document.getElementById("pages-grid")).toBeInTheDocument();
    });

    // Click Select All
    const selectAllBtn = document.getElementById("select-all-btn") as HTMLButtonElement;
    fireEvent.click(selectAllBtn);

    // Batch buttons should appear
    expect(screen.getByRole("button", { name: /Rotate Selected \(3\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Delete Selected \(3\)/i })).toBeInTheDocument();

    // Rotate selected
    const rotateSelectedBtn = screen.getByRole("button", { name: /Rotate Selected \(3\)/i });
    fireEvent.click(rotateSelectedBtn);
    expect(screen.getAllByText("+90°").length).toBe(3);

    // Click Deselect All
    const deselectAllBtn = document.getElementById("deselect-all-btn") as HTMLButtonElement;
    fireEvent.click(deselectAllBtn);
    expect(screen.queryByRole("button", { name: /Rotate Selected/i })).toBeNull();
  });

  it("rejects non-PDF files with error banner", () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const textFile = new File(["not a pdf"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.txt/i)).toBeInTheDocument();
    expect(document.getElementById("global-error-banner")).toBeInTheDocument();
  });

  it("allows clearing selected file", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy content with /Type /Page"], "clear_test.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("clear_test.pdf")).toBeInTheDocument();
    });

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("clear_test.pdf")).toBeNull();
    expect(screen.getByText("Choose a PDF to organize")).toBeInTheDocument();
  });

  it("handles corrupted or untrusted PDF by displaying an error banner instead of crashing", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const corruptedFile = new File(["corrupted garbage bytes"], "corrupted.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [corruptedFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Could not parse PDF pages/i)).toBeInTheDocument();
    });
    expect(document.getElementById("pages-grid")).toBeNull();
  });

  it("handles empty 0-byte PDF file by displaying an error banner", async () => {
    render(<OrganizePdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const emptyFile = new File([], "empty.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [emptyFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Could not parse PDF pages/i)).toBeInTheDocument();
    });
    expect(document.getElementById("pages-grid")).toBeNull();
  });

  it("configures local worker /pdf.worker.min.mjs without loading from external CDN", async () => {
    const pdfjs = await import("pdfjs-dist");
    const GlobalWorkerOptions = pdfjs.GlobalWorkerOptions || (pdfjs as any).default?.GlobalWorkerOptions;
    expect(GlobalWorkerOptions?.workerSrc).toBe("/pdf.worker.min.mjs");
    expect(GlobalWorkerOptions?.workerSrc).not.toContain("cdnjs.cloudflare.com");
  });
});
