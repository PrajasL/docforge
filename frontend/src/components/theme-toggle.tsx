"use client";

import React, { useState, useRef, useEffect } from "react";
import { useTheme, Theme } from "@/context/theme-context";
import { Sun, Moon, Laptop, ChevronDown, Check } from "lucide-react";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleQuickToggle = () => {
    // Quick toggle between light and dark
    if (resolvedTheme === "dark") {
      setTheme("light");
    } else {
      setTheme("dark");
    }
  };

  return (
    <div className={`relative inline-flex items-center ${className}`} ref={menuRef}>
      {/* Quick toggle button */}
      <button
        type="button"
        id="theme-toggle-btn"
        data-testid="theme-toggle"
        onClick={handleQuickToggle}
        aria-label={`Toggle theme (currently ${theme})`}
        title={`Theme: ${theme} (click to toggle light/dark)`}
        className="p-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
      >
        {resolvedTheme === "dark" ? (
          <Moon className="w-4 h-4 text-blue-400 animate-in fade-in" />
        ) : (
          <Sun className="w-4 h-4 text-amber-500 animate-in fade-in" />
        )}
      </button>

      {/* Options dropdown button */}
      <button
        type="button"
        aria-label="Theme menu"
        onClick={() => setIsOpen(!isOpen)}
        className="ml-0.5 p-1 rounded-md text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <ChevronDown className="w-3 h-3" />
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1.5 w-36 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl py-1 z-50 text-xs backdrop-blur-md animate-in fade-in zoom-in-95"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setTheme("light");
              setIsOpen(false);
            }}
            className={`w-full px-3 py-2 flex items-center justify-between text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
              theme === "light"
                ? "font-semibold text-blue-600 dark:text-blue-400"
                : "text-gray-700 dark:text-gray-300"
            }`}
          >
            <span className="flex items-center gap-2">
              <Sun className="w-3.5 h-3.5 text-amber-500" />
              Light
            </span>
            {theme === "light" && <Check className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setTheme("dark");
              setIsOpen(false);
            }}
            className={`w-full px-3 py-2 flex items-center justify-between text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
              theme === "dark"
                ? "font-semibold text-blue-600 dark:text-blue-400"
                : "text-gray-700 dark:text-gray-300"
            }`}
          >
            <span className="flex items-center gap-2">
              <Moon className="w-3.5 h-3.5 text-blue-400" />
              Dark
            </span>
            {theme === "dark" && <Check className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setTheme("system");
              setIsOpen(false);
            }}
            className={`w-full px-3 py-2 flex items-center justify-between text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
              theme === "system"
                ? "font-semibold text-blue-600 dark:text-blue-400"
                : "text-gray-700 dark:text-gray-300"
            }`}
          >
            <span className="flex items-center gap-2">
              <Laptop className="w-3.5 h-3.5 text-gray-500" />
              System
            </span>
            {theme === "system" && <Check className="w-3.5 h-3.5" />}
          </button>
        </div>
      )}
    </div>
  );
}
