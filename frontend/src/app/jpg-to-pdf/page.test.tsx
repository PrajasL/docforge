import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import JpgToPdfPage from "./page";

describe("JPG to PDF Page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = vi.fn(() => "blob:mock-image-url");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("renders page heading, description, and upload button", () => {
    render(<JpgToPdfPage />);
    expect(screen.getByRole("heading", { name: "JPG to PDF" })).toBeInTheDocument();
    expect(screen.getByText("Convert multiple images to a unified PDF")).toBeInTheDocument();
    expect(screen.getByText(/Select or drop JPG images here/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Browse JPG Images/i })).toBeInTheDocument();
  });

  it("handles adding multiple JPG files and displays them in gallery with layout options", () => {
    render(<JpgToPdfPage />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    const file1 = new File(["dummy jpeg data 1"], "photo_1.jpg", { type: "image/jpeg" });
    const file2 = new File(["dummy jpeg data 2"], "photo_2.jpeg", { type: "image/jpeg" });

    fireEvent.change(fileInput, { target: { files: [file1, file2] } });

    expect(screen.getByText("photo_1.jpg")).toBeInTheDocument();
    expect(screen.getByText("photo_2.jpeg")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("Page Layout & Margins")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Convert to PDF/i })).toBeInTheDocument();
  });

  it("allows switching orientation, page size, and margin options", () => {
    render(<JpgToPdfPage />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["dummy jpeg"], "test.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Orientation
    const portraitBtn = screen.getByRole("button", { name: /Portrait/i });
    fireEvent.click(portraitBtn);
    expect(portraitBtn).toHaveClass("border-orange-500");

    const landscapeBtn = screen.getByRole("button", { name: /Landscape/i });
    fireEvent.click(landscapeBtn);
    expect(landscapeBtn).toHaveClass("border-orange-500");

    // Page size
    const a4Btn = screen.getByRole("button", { name: /^A4/i });
    fireEvent.click(a4Btn);
    expect(a4Btn).toHaveClass("border-orange-500");

    const letterBtn = screen.getByRole("button", { name: /US Letter/i });
    fireEvent.click(letterBtn);
    expect(letterBtn).toHaveClass("border-orange-500");

    // Margin
    const smallMarginBtn = screen.getByRole("button", { name: /Small Margin/i });
    fireEvent.click(smallMarginBtn);
    expect(smallMarginBtn).toHaveClass("border-orange-500");
  });

  it("allows removing individual images and clearing all", () => {
    render(<JpgToPdfPage />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file1 = new File(["img1"], "test1.jpg", { type: "image/jpeg" });
    const file2 = new File(["img2"], "test2.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [file1, file2] } });

    expect(screen.getByText("test1.jpg")).toBeInTheDocument();
    expect(screen.getByText("test2.jpg")).toBeInTheDocument();

    // Click remove on the first image
    const removeButtons = screen.getAllByTitle("Remove image");
    fireEvent.click(removeButtons[0]);

    expect(screen.queryByText("test1.jpg")).not.toBeInTheDocument();
    expect(screen.getByText("test2.jpg")).toBeInTheDocument();

    // Clear all
    const clearBtn = screen.getByRole("button", { name: /Clear All/i });
    fireEvent.click(clearBtn);

    expect(screen.queryByText("test2.jpg")).not.toBeInTheDocument();
    expect(screen.getByText(/Select or drop JPG images here/i)).toBeInTheDocument();
  });

  it("rejects non-JPG files with a helpful error alert", () => {
    render(<JpgToPdfPage />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const invalidFile = new File(["plain text"], "notes.txt", { type: "text/plain" });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText(/Only JPG\/JPEG images are accepted\. Skipped: notes\.txt/i)
    ).toBeInTheDocument();
  });
});
