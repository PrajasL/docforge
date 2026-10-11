import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FileQuestion, ArrowLeft, LayoutGrid, Home } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col justify-between">
      {/* Minimal Header */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-2">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold">
            D
          </div>
          <span className="font-bold text-lg tracking-tight">DocForge</span>
        </Link>
        <Link href="/tools">
          <Button variant="outline" size="sm">
            <LayoutGrid className="w-4 h-4 mr-1.5" />
            All Tools
          </Button>
        </Link>
      </header>

      {/* Main 404 Content */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-16">
        <div className="max-w-md w-full text-center space-y-6 animate-in fade-in zoom-in-95 duration-200">
          <div className="w-20 h-20 rounded-3xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900/50 flex items-center justify-center mx-auto shadow-lg shadow-blue-500/10">
            <FileQuestion className="w-10 h-10" />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              Error 404
            </span>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              Page Not Found
            </h1>
            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 max-w-sm mx-auto leading-relaxed">
              The PDF tool or page you are looking for might have been moved, renamed, or does not exist.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link href="/" className="w-full sm:w-auto">
              <Button size="lg" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-2 shadow-md shadow-blue-500/20">
                <Home className="w-4 h-4" />
                Return to Dashboard
              </Button>
            </Link>
            <Link href="/tools" className="w-full sm:w-auto">
              <Button variant="outline" size="lg" className="w-full gap-2">
                <LayoutGrid className="w-4 h-4 text-blue-500" />
                Browse 12 Tools
              </Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-xs text-gray-600 dark:text-gray-400">
        DocForge &bull; Private, Fast, Client-First PDF Utilities
      </footer>
    </div>
  );
}
