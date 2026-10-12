import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "./page";
import { ThemeProvider } from "@/context/theme-context";
import { TOOLS } from "@/config/tools-list";
import { HOMEPAGE_FAQS } from "@/config/tools-seo";

function renderWithProviders(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe("DocForge Production Homepage (UI & SEO)", () => {
  it("renders DocForge brand heading, primary H1, and hero value proposition", () => {
    renderWithProviders(<Home />);

    // Brand logo & title in navbar
    expect(screen.getByRole("link", { name: /docforge homepage/i })).toBeInTheDocument();

    // Primary H1 heading
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent(/free, private & secure/i);
    expect(h1).toHaveTextContent(/online pdf tools/i);

    // Hero description
    expect(
      screen.getByText(/merge, split, compress, rotate, organize, convert, and protect pdf documents/i)
    ).toBeInTheDocument();

    // CTAs
    expect(screen.getByRole("link", { name: /explore all 13 tools/i })).toHaveAttribute("href", "#tools");
    expect(screen.getByRole("link", { name: /most popular: merge pdf/i })).toHaveAttribute("href", "/merge");
  });

  it("renders trust highlights (privacy, auto-cleanup, free, fidelity)", () => {
    renderWithProviders(<Home />);

    expect(screen.getByText("100% Private Sandbox")).toBeInTheDocument();
    expect(screen.getByText("2-Hour Auto-Purge")).toBeInTheDocument();
    expect(screen.getByText("Browser-Grade & Free")).toBeInTheDocument();
    expect(screen.getByText("High Document Fidelity")).toBeInTheDocument();
  });

  it("renders all 13 operational PDF tools with crawlable links and descriptions", () => {
    renderWithProviders(<Home />);

    expect(TOOLS).toHaveLength(13);

    for (const tool of TOOLS) {
      const card = screen.getByTestId(`homepage-tool-card-${tool.id}`);
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute("href", tool.href);
      expect(card).toHaveTextContent(tool.name);
      expect(card).toHaveTextContent(tool.desc);
    }
  });

  it("allows filtering tools by category tabs (Organize, Optimize, Convert, Security)", () => {
    renderWithProviders(<Home />);

    // Tab for Organize
    const organizeTab = screen.getByRole("tab", { name: /organize/i });
    fireEvent.click(organizeTab);

    expect(screen.getByTestId("homepage-tool-card-merge-pdf")).toBeInTheDocument();
    expect(screen.getByTestId("homepage-tool-card-split-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("homepage-tool-card-compress-pdf")).not.toBeInTheDocument();

    // Tab for Optimize
    const optimizeTab = screen.getByRole("tab", { name: /optimize/i });
    fireEvent.click(optimizeTab);

    expect(screen.getByTestId("homepage-tool-card-compress-pdf")).toBeInTheDocument();
    expect(screen.getByTestId("homepage-tool-card-repair-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("homepage-tool-card-merge-pdf")).not.toBeInTheDocument();

    // Tab for Security
    const securityTab = screen.getByRole("tab", { name: /security/i });
    fireEvent.click(securityTab);

    expect(screen.getByTestId("homepage-tool-card-protect-pdf")).toBeInTheDocument();
    expect(screen.getByTestId("homepage-tool-card-unlock-pdf")).toBeInTheDocument();
    expect(screen.getByTestId("homepage-tool-card-watermark-pdf")).toBeInTheDocument();
    expect(screen.queryByTestId("homepage-tool-card-merge-pdf")).not.toBeInTheDocument();

    // Tab for All Tools
    const allTab = screen.getByRole("tab", { name: /all tools/i });
    fireEvent.click(allTab);

    expect(screen.getByTestId("homepage-tool-card-merge-pdf")).toBeInTheDocument();
    expect(screen.getByTestId("homepage-tool-card-repair-pdf")).toBeInTheDocument();
  });

  it("renders 'How DocForge Works' with 3 sequential steps", () => {
    renderWithProviders(<Home />);

    expect(screen.getByRole("heading", { name: /how docforge works/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Select & Configure")).toBeInTheDocument();
    expect(screen.getByText("Isolated Processing")).toBeInTheDocument();
    expect(screen.getByText("Instant Download & Auto-Purge")).toBeInTheDocument();
  });

  it("renders 'Privacy & Security by Design' section with factual guarantees", () => {
    renderWithProviders(<Home />);

    expect(screen.getByRole("heading", { name: /engineered for complete document privacy/i })).toBeInTheDocument();
    expect(screen.getByText("Automated Lifecycle Purge")).toBeInTheDocument();
    expect(screen.getByText("Zero Third-Party Cloud Leaks")).toBeInTheDocument();
    expect(screen.getByText("No AI Model Training")).toBeInTheDocument();
    expect(screen.getByText("MIME & Magic-Byte Inspection")).toBeInTheDocument();
  });

  it("renders Frequently Asked Questions matching the FAQ data", () => {
    renderWithProviders(<Home />);

    expect(screen.getByRole("heading", { name: /frequently asked questions/i, level: 2 })).toBeInTheDocument();

    for (const faq of HOMEPAGE_FAQS) {
      expect(screen.getByText(faq.question)).toBeInTheDocument();
      expect(screen.getByText(faq.answer)).toBeInTheDocument();
    }
  });

  it("injects valid JSON-LD structured data matching Schema.org specifications", () => {
    const { container } = renderWithProviders(<Home />);

    const scriptTag = container.querySelector('script[type="application/ld+json"]');
    expect(scriptTag).toBeInTheDocument();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@graph"]).toBeDefined();
    expect(Array.isArray(jsonLd["@graph"])).toBe(true);

    const types = (jsonLd["@graph"] as { "@type": string }[]).map((item) => item["@type"]);
    expect(types).toContain("WebSite");
    expect(types).toContain("WebApplication");
    expect(types).toContain("FAQPage");
  });

  it("renders comprehensive footer with tool links, how-it-works, security, and legal links", () => {
    renderWithProviders(<Home />);

    expect(screen.getByRole("link", { name: /all 13 tools directory/i })).toHaveAttribute("href", "/tools");
    const privacyLinks = screen.getAllByRole("link", { name: /privacy policy/i });
    expect(privacyLinks.length).toBeGreaterThan(0);
    privacyLinks.forEach((link) => expect(link).toHaveAttribute("href", "/privacy"));

    const termsLinks = screen.getAllByRole("link", { name: /terms of service/i });
    expect(termsLinks.length).toBeGreaterThan(0);
    termsLinks.forEach((link) => expect(link).toHaveAttribute("href", "/terms"));
  });
});
