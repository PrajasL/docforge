import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Navbar } from "./navbar";
import { ThemeProvider } from "@/context/theme-context";

function renderWithProviders(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe("Navbar Component", () => {
  it("renders DocForge brand logo linking to root", () => {
    renderWithProviders(<Navbar />);

    const brandLink = screen.getByRole("link", { name: /docforge homepage/i });
    expect(brandLink).toBeInTheDocument();
    expect(brandLink).toHaveAttribute("href", "/");
    expect(screen.getByText("DocForge")).toBeInTheDocument();
  });

  it("renders breadcrumb when currentToolName is provided", () => {
    renderWithProviders(<Navbar currentToolName="Merge PDF" />);

    expect(screen.getByText("Merge PDF")).toBeInTheDocument();
  });

  it("renders desktop navigation links to tools, how it works, and security", () => {
    renderWithProviders(<Navbar />);

    const toolsLink = screen.getByRole("link", { name: /all tools/i });
    expect(toolsLink).toHaveAttribute("href", "/tools");

    const howItWorksLink = screen.getByRole("link", { name: /how it works/i });
    expect(howItWorksLink).toHaveAttribute("href", "/#how-it-works");

    const securityLink = screen.getByRole("link", { name: /security & privacy/i });
    expect(securityLink).toHaveAttribute("href", "/#security");
  });

  it("toggles mobile menu drawer with correct ARIA attributes and closes on Escape", () => {
    renderWithProviders(<Navbar />);

    const toggleButton = screen.getByRole("button", { name: /open navigation menu/i });
    expect(toggleButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: /mobile navigation/i })).not.toBeInTheDocument();

    // Open mobile menu
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute("aria-expanded", "true");
    const mobileNav = screen.getByRole("region", { name: /mobile navigation/i });
    expect(mobileNav).toBeInTheDocument();

    // Verify links in mobile nav
    expect(screen.getByRole("link", { name: /all 13 pdf tools/i })).toHaveAttribute("href", "/tools");

    // Press Escape to close
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("region", { name: /mobile navigation/i })).not.toBeInTheDocument();
  });
});
