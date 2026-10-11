import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PrivacyPolicyPage from "./privacy/page";
import TermsOfServicePage from "./terms/page";
import { ThemeProvider } from "@/context/theme-context";

function renderWithTheme(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe("Legal Pages (Privacy Policy & Terms of Service)", () => {
  describe("Privacy Policy Page (/privacy)", () => {
    it("renders Privacy Policy heading, badges, and breadcrumbs", () => {
      renderWithTheme(<PrivacyPolicyPage />);

      expect(
        screen.getByRole("heading", { level: 1, name: /privacy policy/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/transparent data processing policy/i)).toBeInTheDocument();
      expect(screen.getByText(/back to dashboard/i)).toBeInTheDocument();
      expect(screen.getByText(/skip to main content/i)).toBeInTheDocument();
    });

    it("truthfully discloses 2-hour purge, backend processing, and zero third-party APIs", () => {
      renderWithTheme(<PrivacyPolicyPage />);

      expect(screen.getByText(/2-hour auto-purge/i)).toBeInTheDocument();
      expect(screen.getByText(/zero third-party apis/i)).toBeInTheDocument();
      expect(screen.getByText(/ephemeral passwords/i)).toBeInTheDocument();
      expect(screen.getByText(/how document processing works/i)).toBeInTheDocument();
      expect(screen.getByText(/antivirus and malware scanning/i)).toBeInTheDocument();
      expect(screen.getByText(/telemetry and error scrubbing guarantees/i)).toBeInTheDocument();
    });

    it("clearly presents operator customization requirements for launch", () => {
      renderWithTheme(<PrivacyPolicyPage />);

      expect(
        screen.getByText(/operator notice: production legal customization required/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/legal entity & operator/i)).toBeInTheDocument();
      expect(screen.getByText(/contact & dpo email/i)).toBeInTheDocument();
    });
  });

  describe("Terms of Service Page (/terms)", () => {
    it("renders Terms of Service heading, fair use badge, and back link", () => {
      renderWithTheme(<TermsOfServicePage />);

      expect(
        screen.getByRole("heading", { level: 1, name: /terms of service/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/operational terms & fair use policy/i)).toBeInTheDocument();
      expect(screen.getByText(/back to dashboard/i)).toBeInTheDocument();
    });

    it("documents actual resource boundaries and 2-hour retention policy", () => {
      renderWithTheme(<TermsOfServicePage />);

      expect(screen.getByText(/your documents, your rights/i)).toBeInTheDocument();
      expect(screen.getByText(/transient utility only/i)).toBeInTheDocument();
      expect(screen.getByText(/strict malware defense/i)).toBeInTheDocument();
      expect(screen.getByText(/service boundaries and enforced resource limits/i)).toBeInTheDocument();
      expect(screen.getByText(/mandatory 2-hour expiration/i)).toBeInTheDocument();
      expect(screen.getByText(/50 mb per pdf/i)).toBeInTheDocument();
    });

    it("highlights operator legal jurisdiction and arbitration customization requirements", () => {
      renderWithTheme(<TermsOfServicePage />);

      expect(
        screen.getByText(/operator notice: production legal customization required/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/governing law & jurisdiction/i)).toBeInTheDocument();
      expect(screen.getByText(/notice \/ legal contact address/i)).toBeInTheDocument();
    });
  });
});
