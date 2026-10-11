import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ToolHeader } from "./tool-header";
import { Layers } from "lucide-react";

describe("ToolHeader Component", () => {
  it("renders tool name, default badge, and icon", () => {
    render(<ToolHeader toolName="Merge PDF" icon={Layers} iconBgColor="bg-blue-600" />);

    expect(screen.getByText("Merge PDF")).toBeInTheDocument();
    expect(screen.getByText("DocForge Tools")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Go back/i })).toBeInTheDocument();
  });

  it("renders custom badge and back link href", () => {
    render(
      <ToolHeader
        toolName="Rotate PDF"
        icon={Layers}
        badge="Custom Badge"
        backHref="/tools"
      />
    );

    expect(screen.getByText("Rotate PDF")).toBeInTheDocument();
    expect(screen.getByText("Custom Badge")).toBeInTheDocument();
    const backLink = screen.getByRole("link", { name: /Go back/i });
    expect(backLink).toHaveAttribute("href", "/tools");
  });

  it("renders All Tools and Dashboard navigation buttons", () => {
    render(<ToolHeader toolName="Compress PDF" icon={Layers} />);

    const allToolsLink = screen.getByRole("link", { name: /All Tools/i });
    expect(allToolsLink).toHaveAttribute("href", "/tools");

    const dashboardLink = screen.getByRole("link", { name: /Dashboard/i });
    expect(dashboardLink).toHaveAttribute("href", "/");
  });

  it("renders ThemeToggle", () => {
    render(<ToolHeader toolName="Watermark PDF" icon={Layers} />);

    expect(screen.getByRole("button", { name: /toggle theme/i })).toBeInTheDocument();
  });
});
