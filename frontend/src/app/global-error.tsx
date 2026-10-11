"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { AlertOctagon, RefreshCw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
            <AlertOctagon className="w-8 h-8" />
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold">Fatal Application Error</h1>
            <p className="text-sm text-gray-600">
              The application encountered a critical error during execution.
            </p>
          </div>
          <Button onClick={() => reset()} className="bg-blue-600 text-white gap-2">
            <RefreshCw className="w-4 h-4" />
            Reload DocForge
          </Button>
        </div>
      </body>
    </html>
  );
}
