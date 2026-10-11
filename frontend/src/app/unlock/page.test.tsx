import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import UnlockPdfPage from "./page";

describe("Unlock PDF Page", () => {
  it("renders page heading, description, and upload button", () => {
    render(<UnlockPdfPage />);
    expect(screen.getByRole("heading", { name: "Unlock Password-Protected PDF" })).toBeInTheDocument();
    expect(screen.getByText("Choose a password-protected PDF to unlock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select Protected PDF/i })).toBeInTheDocument();
  });

  it("handles adding a protected PDF file and displays file info and password input", () => {
    render(<UnlockPdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy encrypted pdf content"], "protected_vault.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("protected_vault.pdf")).toBeInTheDocument();
    expect(screen.getByText("Enter Document Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Unlock PDF/i })).toBeInTheDocument();
  });

  it("allows entering password and toggling visibility between text and password", () => {
    render(<UnlockPdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "protected_secret.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const passwordInput = document.getElementById("password-input") as HTMLInputElement;
    const toggleBtn = document.getElementById("toggle-password-visibility-btn");

    expect(passwordInput.type).toBe("password");
    fireEvent.change(passwordInput, { target: { value: "DecryptKey123" } });
    expect(passwordInput.value).toBe("DecryptKey123");

    // Toggle to visible text
    fireEvent.click(toggleBtn!);
    expect(passwordInput.type).toBe("text");

    // Toggle back to hidden
    fireEvent.click(toggleBtn!);
    expect(passwordInput.type).toBe("password");
  });

  it("rejects non-PDF files with an error message banner", () => {
    render(<UnlockPdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const textFile = new File(["plain text content"], "notes.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });

    expect(screen.getByText(/Skipped non-PDF file: notes.txt/i)).toBeInTheDocument();
    expect(document.getElementById("global-error-banner")).toBeInTheDocument();
  });

  it("allows clearing selected file to return to upload dropzone", () => {
    render(<UnlockPdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "protected_doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("protected_doc.pdf")).toBeInTheDocument();

    const changeBtn = screen.getByRole("button", { name: /Change File/i });
    fireEvent.click(changeBtn);

    expect(screen.queryByText("protected_doc.pdf")).toBeNull();
    expect(screen.getByText("Choose a password-protected PDF to unlock")).toBeInTheDocument();
  });

  it("disables unlock submit button when password is empty", () => {
    render(<UnlockPdfPage />);
    const fileInput = document.getElementById("pdf-upload-input") as HTMLInputElement;

    const file = new File(["dummy pdf"], "protected_doc.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitBtn = document.getElementById("unlock-submit-btn") as HTMLButtonElement;
    expect(submitBtn).toBeDisabled();

    const passwordInput = document.getElementById("password-input") as HTMLInputElement;
    fireEvent.change(passwordInput, { target: { value: "some_password" } });
    expect(submitBtn).not.toBeDisabled();
  });
});
