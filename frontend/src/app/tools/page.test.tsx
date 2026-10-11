import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import AllToolsPage, { TOOLS } from "./page";
import { ThemeProvider } from "@/context/theme-context";

function renderWithProviders(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe("All Tools Directory Page (/tools)", () => {
  it("renders page title, subtitle, search input, and category tabs", () => {
    renderWithProviders(<AllToolsPage />);

    expect(screen.getByRole("heading", { name: /all pdf tools/i, level: 1 })).toBeInTheDocument();
    expect(screen.getByTestId("tool-search-input")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /all tools/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /organize/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /optimize/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /convert/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /security/i })).toBeInTheDocument();
  });

  it("renders all 13 active tools by default", () => {
    renderWithProviders(<AllToolsPage />);

    expect(TOOLS.length).toBe(13);

    TOOLS.forEach((tool) => {
      expect(screen.getByTestId(`tool-card-${tool.id}`)).toBeInTheDocument();
      expect(screen.getByText(tool.name)).toBeInTheDocument();
    });

    expect(screen.getByText(/showing 13 of 13 tools/i)).toBeInTheDocument();
  });

  it("filters tools by text search input", () => {
    renderWithProviders(<AllToolsPage />);

    const searchInput = screen.getByTestId("tool-search-input");
    fireEvent.change(searchInput, { target: { value: "merge" } });

    expect(screen.getByTestId("tool-card-merge-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("tool-card-compress-pdf")).not.toBeInTheDocument();
    expect(screen.queryByTestId("tool-card-split-pdf")).not.toBeInTheDocument();
  });

  it("filters tools by keywords in search query (e.g. 'encrypt')", () => {
    renderWithProviders(<AllToolsPage />);

    const searchInput = screen.getByTestId("tool-search-input");
    fireEvent.change(searchInput, { target: { value: "encrypt" } });

    // Protect PDF has "encrypt" keyword
    expect(screen.getByTestId("tool-card-protect-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("tool-card-merge-pdf")).not.toBeInTheDocument();
  });

  it("filters tools by category tab", () => {
    renderWithProviders(<AllToolsPage />);

    // Click 'Convert' category
    const convertTab = screen.getByRole("tab", { name: /convert/i });
    fireEvent.click(convertTab);

    expect(screen.getByTestId("tool-card-pdf-to-jpg")).toBeInTheDocument();
    expect(screen.getByTestId("tool-card-jpg-to-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("tool-card-merge-pdf")).not.toBeInTheDocument();
    expect(screen.getByText(/showing 2 of 13 tools/i)).toBeInTheDocument();
  });

  it("displays empty state when query matches no tools and resets properly", () => {
    renderWithProviders(<AllToolsPage />);

    const searchInput = screen.getByTestId("tool-search-input");
    fireEvent.change(searchInput, { target: { value: "nonexistenttool1234" } });

    expect(screen.getByTestId("empty-tools-state")).toBeInTheDocument();
    expect(screen.getByText(/no tools found/i)).toBeInTheDocument();

    // Click Reset Search & Filters button
    const resetBtn = screen.getByRole("button", { name: /reset search & filters/i });
    fireEvent.click(resetBtn);

    expect(screen.queryByTestId("empty-tools-state")).not.toBeInTheDocument();
    expect(screen.getByTestId("tool-card-merge-pdf")).toBeInTheDocument();
    expect(screen.getByText(/showing 13 of 13 tools/i)).toBeInTheDocument();
  });
});
