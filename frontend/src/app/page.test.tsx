import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "./page";

describe("DocForge Placeholder Page", () => {
  it("renders DocForge brand heading and Phase 1 badge", () => {
    render(<Home />);
    expect(screen.getByText("DocForge")).toBeInTheDocument();
    expect(screen.getByText("Phase 1: Foundation")).toBeInTheDocument();
  });

  it("renders the upcoming tools preview list", () => {
    render(<Home />);
    expect(screen.getByText("Merge PDF")).toBeInTheDocument();
    expect(screen.getByText("Split PDF")).toBeInTheDocument();
    expect(screen.getByText("Compress PDF")).toBeInTheDocument();
    expect(screen.getByText("Rotate PDF")).toBeInTheDocument();
    expect(screen.getByText("PDF to JPG")).toBeInTheDocument();
    expect(screen.getByText("JPG to PDF")).toBeInTheDocument();
  });

  it("renders infrastructure services cards", () => {
    render(<Home />);
    expect(screen.getByText("FastAPI Backend")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL 16")).toBeInTheDocument();
    expect(screen.getByText("Redis 7")).toBeInTheDocument();
    expect(screen.getByText("MinIO Storage")).toBeInTheDocument();
  });
});
