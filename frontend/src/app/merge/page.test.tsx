import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MergePdfPage from "./page";

describe("Merge PDF Page", () => {
  it("renders page heading, description, and file dropzone", () => {
    render(<MergePdfPage />);
    expect(screen.getByRole("heading", { name: "Merge PDF Files" })).toBeInTheDocument();
    expect(
      screen.getByText("Choose PDF files or drag & drop them here")
    ).toBeInTheDocument();
  });

  it("handles adding PDF files and displays them in the list", () => {
    render(<MergePdfPage />);
    const fileInput = document.getElementById("merge-file-input") as HTMLInputElement;

    const fileA = new File(["dummy a"], "document_a.pdf", { type: "application/pdf" });
    const fileB = new File(["dummy b"], "document_b.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [fileA, fileB] } });

    expect(screen.getByText("document_a.pdf")).toBeInTheDocument();
    expect(screen.getByText("document_b.pdf")).toBeInTheDocument();
    expect(screen.getByText("Selected Files (2)")).toBeInTheDocument();

    const mergeBtn = screen.getByRole("button", { name: /Merge 2 Files/i });
    expect(mergeBtn).not.toBeDisabled();
  });

  it("allows reordering files with Move Down and Move Up buttons", () => {
    render(<MergePdfPage />);
    const fileInput = document.getElementById("merge-file-input") as HTMLInputElement;

    const fileA = new File(["a"], "alpha.pdf", { type: "application/pdf" });
    const fileB = new File(["b"], "beta.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [fileA, fileB] } });

    // Initial order: alpha is index 0, beta is index 1
    const moveDownBtn = screen.getByLabelText("Move alpha.pdf down");
    fireEvent.click(moveDownBtn);

    // After move down, beta is first, alpha is second
    const items = screen.getAllByTestId(/file-item-/);
    expect(items[0]).toHaveTextContent("beta.pdf");
    expect(items[1]).toHaveTextContent("alpha.pdf");

    // Move alpha back up
    const moveUpBtn = screen.getByLabelText("Move alpha.pdf up");
    fireEvent.click(moveUpBtn);
    const updatedItems = screen.getAllByTestId(/file-item-/);
    expect(updatedItems[0]).toHaveTextContent("alpha.pdf");
    expect(updatedItems[1]).toHaveTextContent("beta.pdf");
  });

  it("allows removing a selected file and updates file count", () => {
    render(<MergePdfPage />);
    const fileInput = document.getElementById("merge-file-input") as HTMLInputElement;

    const fileA = new File(["a"], "file1.pdf", { type: "application/pdf" });
    const fileB = new File(["b"], "file2.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [fileA, fileB] } });
    expect(screen.getByText("file1.pdf")).toBeInTheDocument();

    const removeBtn = screen.getByLabelText("Remove file1.pdf");
    fireEvent.click(removeBtn);

    expect(screen.queryByText("file1.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("file2.pdf")).toBeInTheDocument();
    expect(screen.getByText("Selected Files (1)")).toBeInTheDocument();

    // With only 1 file, merge button should be disabled
    const mergeBtn = screen.getByRole("button", { name: /Merge 1 Files/i });
    expect(mergeBtn).toBeDisabled();
  });

  it("rejects non-PDF files with an error banner", () => {
    render(<MergePdfPage />);
    const fileInput = document.getElementById("merge-file-input") as HTMLInputElement;

    const textFile = new File(["txt"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF files: notes.txt/i)).toBeInTheDocument();
  });
});
