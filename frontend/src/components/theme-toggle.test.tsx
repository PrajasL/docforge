import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ThemeToggle } from "./theme-toggle";
import { ThemeProvider, useTheme } from "@/context/theme-context";

function ThemeConsumer() {
  const { theme, resolvedTheme } = useTheme();
  return (
    <div>
      <span data-testid="current-theme">{theme}</span>
      <span data-testid="resolved-theme">{resolvedTheme}</span>
      <ThemeToggle />
    </div>
  );
}

describe("Theme System & ThemeToggle Component", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    // Mock matchMedia
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("defaults to system theme and respects light system preference", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("current-theme").textContent).toBe("system");
    expect(screen.getByTestId("resolved-theme").textContent).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggles theme between dark and light on click and updates localStorage", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    const toggleBtn = screen.getByTestId("theme-toggle");
    
    // Quick toggle: light -> dark
    act(() => {
      fireEvent.click(toggleBtn);
    });

    expect(localStorage.getItem("docforge_theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // Quick toggle: dark -> light
    act(() => {
      fireEvent.click(toggleBtn);
    });

    expect(localStorage.getItem("docforge_theme")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("opens options dropdown and selects dark theme", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    const menuBtn = screen.getByLabelText(/theme menu/i);
    fireEvent.click(menuBtn);

    const darkOption = screen.getByRole("menuitem", { name: /dark/i });
    act(() => {
      fireEvent.click(darkOption);
    });

    expect(localStorage.getItem("docforge_theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("loads stored dark preference from localStorage on mount", () => {
    localStorage.setItem("docforge_theme", "dark");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("current-theme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
