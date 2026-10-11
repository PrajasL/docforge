import React from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { ArrowLeft, LayoutGrid, Home as HomeIcon } from "lucide-react";

export interface ToolHeaderProps {
  toolName: string;
  icon: React.ComponentType<{ className?: string }>;
  iconBgColor?: string;
  iconColor?: string;
  badge?: string;
  backHref?: string;
}

export function ToolHeader({
  toolName,
  icon: Icon,
  iconBgColor = "bg-blue-600",
  iconColor = "text-white",
  badge = "DocForge Tools",
  backHref = "/",
}: ToolHeaderProps) {
  const handleBack = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      e.preventDefault();
      window.history.back();
    }
  };

  return (
    <header className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Back Link + Tool Icon + Tool Title + Badge */}
        <div className="flex items-center space-x-3 min-w-0">
          <Link
            href={backHref}
            onClick={handleBack}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors shrink-0"
            title="Go back"
            aria-label="Go back"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Back</span>
          </Link>

          <div
            className={`w-9 h-9 rounded-xl ${iconBgColor} flex items-center justify-center ${iconColor} shadow-md shadow-black/5 shrink-0`}
          >
            <Icon className="w-5 h-5" />
          </div>

          <div className="flex items-center min-w-0">
            <span className="font-bold text-lg sm:text-xl tracking-tight text-gray-900 dark:text-white truncate">
              {toolName}
            </span>
            <span className="hidden sm:inline-flex items-center ml-2.5 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/60 shrink-0">
              {badge}
            </span>
          </div>
        </div>

        {/* Right: All Tools + Dashboard + Theme Toggle */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          <Link href="/tools">
            <Button
              variant="outline"
              size="sm"
              className="hidden sm:inline-flex items-center gap-1.5 text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white"
            >
              <LayoutGrid className="w-4 h-4 text-blue-500" />
              All Tools
            </Button>
          </Link>
          <Link href="/">
            <Button
              variant="outline"
              size="sm"
              className="inline-flex items-center gap-1.5 text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white"
            >
              <HomeIcon className="w-4 h-4 text-gray-500" />
              <span>Dashboard</span>
            </Button>
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
