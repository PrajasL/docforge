import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ProtectPdfPage from "./page";

describe("Protect PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<ProtectPdfPage />);
    expect(screen.getByRole("heading", { name: "Protect PDF with Password" })).toBeInTheDocument();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Choose PDF File/i })).toBeInTheDocument();
  });

  it("handles adding a PDF file and displays file info and password form", () => {
    render(<ProtectPdfPage />);
    const fileInput = document.getElementById("protect-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf content"], "confidential_record.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("confidential_record.pdf")).toBeInTheDocument();
    expect(screen.getByText("Set Document Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Protect PDF with Password/i })).toBeInTheDocument();
  });

  it("allows typing password and toggling visibility", () => {
    render(<ProtectPdfPage />);
    const fileInput = document.getElementById("protect-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const passwordInput = document.getElementById("password-input") as HTMLInputElement;
    const toggleBtn = document.getElementById("toggle-password-visibility-btn");

    expect(passwordInput.type).toBe("password");
    fireEvent.change(passwordInput, { target: { value: "MySecret123" } });
    expect(passwordInput.value).toBe("MySecret123");

    // Toggle to visible
    fireEvent.click(toggleBtn!);
    expect(passwordInput.type).toBe("text");

    // Toggle back to hidden
    fireEvent.click(toggleBtn!);
    expect(passwordInput.type).toBe("password");
  });

  it("indicates matching and mismatched passwords", () => {
    render(<ProtectPdfPage />);
    const fileInput = document.getElementById("protect-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const passwordInput = document.getElementById("password-input") as HTMLInputElement;
    const confirmInput = document.getElementById("confirm-password-input") as HTMLInputElement;

    fireEvent.change(passwordInput, { target: { value: "Password123" } });
    fireEvent.change(confirmInput, { target: { value: "DifferentPass" } });

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument();

    fireEvent.change(confirmInput, { target: { value: "Password123" } });
    expect(screen.getByText("Passwords match")).toBeInTheDocument();
  });

  it("rejects non-PDF files with an error message", () => {
    render(<ProtectPdfPage />);
    const fileInput = document.getElementById("protect-file-input") as HTMLInputElement;

    const textFile = new File(["not a pdf"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.txt/i)).toBeInTheDocument();
  });

  it("allows clearing selected file", () => {
    render(<ProtectPdfPage />);
    const fileInput = document.getElementById("protect-file-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "clear_test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("clear_test.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("clear_test.pdf")).toBeNull();
    expect(screen.getByText("Upload your PDF file")).toBeInTheDocument();
  });
});
