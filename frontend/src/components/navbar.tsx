"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { FileText, LayoutGrid, Shield, HelpCircle, Menu, X, ArrowUpRight } from "lucide-react";

interface NavbarProps {
  currentToolName?: string;
  badge?: string;
}

export function Navbar({ currentToolName, badge }: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile drawer on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  return (
    <header className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Optional Tool Breadcrumb */}
        <div className="flex items-center space-x-3">
          <Link
            href="/"
            aria-label="DocForge Homepage"
            className="flex items-center space-x-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg p-1"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
                DocForge
              </span>
              <span className="ml-2 px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                {badge || "Free & Private"}
              </span>
            </div>
          </Link>

          {currentToolName && (
            <div className="hidden sm:flex items-center text-sm text-gray-400">
              <span className="mx-2">/</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {currentToolName}
              </span>
            </div>
          )}
        </div>

        {/* Desktop Nav Links & Controls */}
        <nav aria-label="Main Navigation" className="hidden md:flex items-center space-x-2">
          <Link
            href="/tools"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <LayoutGrid className="w-4 h-4 text-blue-500" />
            All Tools
          </Link>
          <Link
            href="/#how-it-works"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <HelpCircle className="w-4 h-4 text-gray-400" />
            How It Works
          </Link>
          <Link
            href="/#security"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Shield className="w-4 h-4 text-gray-400" />
            Security & Privacy
          </Link>

          <div className="h-4 w-px bg-gray-200 dark:bg-gray-800 mx-1" />

          {/* Theme Toggle */}
          <ThemeToggle />
        </nav>

        {/* Mobile Hamburger & Theme Toggle */}
        <div className="flex md:hidden items-center space-x-2">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
            aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          id="mobile-navigation"
          role="region"
          aria-label="Mobile Navigation"
          className="md:hidden border-t border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-900/95 px-4 pt-3 pb-5 space-y-2 backdrop-blur animate-in slide-in-from-top-2"
        >
          <Link
            href="/tools"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <span className="flex items-center gap-2.5">
              <LayoutGrid className="w-4 h-4 text-blue-500" />
              All 13 PDF Tools
            </span>
            <ArrowUpRight className="w-4 h-4 text-gray-400" />
          </Link>
          <Link
            href="/#how-it-works"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <HelpCircle className="w-4 h-4 text-gray-400" />
            How It Works
          </Link>
          <Link
            href="/#security"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <Shield className="w-4 h-4 text-gray-400" />
            Security & Privacy
          </Link>
          <Link
            href="/privacy"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <span>Privacy Policy</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-400" />
          </Link>
          <Link
            href="/terms"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <span>Terms of Service</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-400" />
          </Link>
        </div>
      )}
    </header>
  );
}
