# Project Status

> **Master Roadmap:** For the full multi-phase delivery plan, feature statuses, technical risk matrix, and launch readiness checklist, see [PROJECT_ROADMAP.md](file:///c:/Users/praja/Documents/AI_PROJECTS/PDF_PROJECT/PROJECT_ROADMAP.md).

## Current Phase: Phase 4.0 — Core Conversion & File Format Expansion (Part 22 Complete & Verified &rarr; Part 23 PDF to Word Next)

**Last updated:** 2026-10-11

---

## Status Summary

| Phase | Status | Progress |
|---|---|---|
| Phase 0: Planning & Setup | ✅ Complete | 100% |
| Phase 1: Foundation (Merge PDF) | ✅ Complete | 100% |
| Phase 2: Core Tools (Split, Compress, Rotate, Watermark, Page Numbers, Protect, Unlock, Extract Pages, Organize PDF, PDF to JPG, JPG to PDF) | ✅ Complete | 100% (All 12 Core Tools Complete) |
| Phase 2.5: Platform Polish & Shared UX (Part 17 Directory/Theme/SSE, Part 18 SEO Architecture & Content) | ✅ Complete | 100% (Phase 2.5 Complete) |
| Phase 3: Launch Readiness & Production (Part 19 Security & Rate Limiting, Part 20 Production Pipeline & Cloud Storage, Part 21 E2E Testing, Accessibility & Legal Pages) | ✅ Complete | 100% (Phase 3 Complete) |
| Phase 4: Core Conversion Suite (Part 22 PDF Repair Complete & Verified &rarr; Part 23 PDF to Word Next) | 🔄 In Progress | 25% (Part 22 Complete) |


---

## Implemented Tool Capabilities

| Tool | Status | Backend Handler | Frontend Route | Test Coverage |
|---|---|---|---|---|
| **Merge PDF** | ✅ Production Ready | `MergePDFHandler` (`pypdf`) | `/merge` | 42 backend tests + 5 frontend tests |
| **Split PDF** | ✅ Production Ready | `SplitPDFHandler` (`pypdf` + `zipfile`) | `/split` | 6 unit + 1 live worker integration test + 7 frontend tests |
| **Compress PDF**| ✅ Production Ready | `CompressPDFHandler` (`pikepdf` + `Pillow`) | `/compress` | 6 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |
| **Rotate PDF**  | ✅ Production Ready | `RotatePDFHandler` (`pypdf`) | `/rotate` | 5 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |
| **Watermark PDF**| ✅ Production Ready | `WatermarkPDFHandler` (`reportlab` + `pypdf`) | `/watermark` | 5 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |
| **Page Numbers**| ✅ Production Ready | `PageNumbersPDFHandler` (`reportlab` + `pypdf`) | `/page-numbers` | 6 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |
| **Protect PDF** | ✅ Production Ready | `ProtectPDFHandler` (`pypdf` + `cryptography` AES-256) | `/protect` | 4 unit + 1 live worker integration test + 6 frontend tests + Real Browser Verification |
| **Unlock PDF**  | ✅ Production Ready | `UnlockPDFHandler` (`pypdf` Decryption) | `/unlock` | 7 unit + 1 live worker integration test + 6 frontend tests + Real Browser Verification |
| **Extract Pages**| ✅ Production Ready | `ExtractPagesPDFHandler` (`pypdf`) | `/extract-pages` | 8 unit + 1 live worker integration test + 13 frontend tests + Real Browser Verification |
| **Organize PDF**| ✅ Production Ready | `OrganizePDFHandler` (`pypdf`) | `/organize-pdf` | 7 unit + 1 live worker integration test + 11 frontend tests + Real Browser Verification |
| **PDF to JPG**  | ✅ Production Ready | `PdfToJpgPDFHandler` (`pypdfium2` + `Pillow`) | `/pdf-to-jpg` | 15 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |
| **JPG to PDF**  | ✅ Production Ready | `JpgToPdfPDFHandler` (`reportlab` + `Pillow`) | `/jpg-to-pdf` | 11 unit + 1 live worker integration test + 5 frontend tests + Real Browser Verification |
| **Repair PDF**  | ✅ Production Ready | `RepairPDFHandler` (`pikepdf`/QPDF + `pypdf` fallback) | `/repair-pdf` | 9 unit + 1 live worker integration test + 7 frontend tests + Real Browser Verification |

---

## Implemented Platform Capabilities (Part 17)

| Feature | Status | Implementation | Routes / Endpoints | Test Coverage |
|---|---|---|---|---|
| **All Tools Directory** | ✅ Production Ready | Next.js searchable directory with category filters | `/tools` | 4 frontend unit tests + Real Browser Verification |
| **Theme System (Dark/Light)** | ✅ Production Ready | `ThemeProvider`, `ThemeToggle`, zero-FOUC script, localStorage | Global Navigation (`/`, `/tools`, all 12 tools) | 4 frontend unit tests + Real Browser Verification |
| **Real-Time Job Progress (SSE)** | ✅ Production Ready | FastAPI `StreamingResponse` + Redis Pub/Sub | `GET /api/v1/jobs/{id}/progress` | 5 backend tests + 5 frontend hook tests + Real Browser Verification |
| **Branded Error Pages** | ✅ Production Ready | Custom DocForge 404 & 500 pages | `not-found.tsx`, `error.tsx`, `global-error.tsx` | Next.js build compilation + Real Browser Verification |

---

## Compress PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pikepdf` (MPL 2.0) + QPDF (Apache 2.0) for object streams, stream Deflate compression, unreferenced object pruning, and cross-reference stream compaction.
  - `Pillow` (HPND / Permissive) for image extraction, downsampling, and JPEG re-encoding.
  - Ghostscript (AGPL) and PyMuPDF (AGPL) were explicitly rejected to preserve permissive commercial compliance.
- **Tiers**:
  1. `recommended`: JPEG quality 80, max dimension 1600px. Standard compression with negligible visual quality impact.
  2. `balanced`: JPEG quality 60, max dimension 1200px. Strong compression with minor downsampling.
  3. `maximum`: JPEG quality 40, max dimension 800px. Extreme compression for strict file size limits.
- **Negative Savings Prevention**:
  - If output is larger than or equal to input (e.g. document already optimal or contains high-entropy streams), the original file is preserved, returning `savings_bytes: 0`, `savings_percentage: 0.0`, and `is_already_optimal: true`.
- **UI & UX**: Responsive Next.js page at `/compress` with drag-and-drop dropzone, tier cards, explanatory quality notice, original vs compressed size display, savings badge, and direct download.

---

## Live Browser Verification Results (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Recommended Mode** | `compress_test_multipage.pdf` (68,953 B) | 49,830 B (Saved 19,123 B / 27.7%) | ✅ Downloaded, opened with pikepdf, verified 2 pages intact |
| **Balanced Mode** | `compress_test_multipage.pdf` (68,953 B) | 42,755 B (Saved 26,198 B / 38.0%) | ✅ Downloaded, opened with pikepdf, verified 2 pages intact |
| **Maximum Mode** | `compress_test_multipage.pdf` (68,953 B) | 8,770 B (Saved 60,183 B / 87.3%) | ✅ Downloaded, opened with pikepdf, verified 2 pages intact |
| **Already-Optimal PDF** | `already_compressed.pdf` (591 B) | 591 B (0% saved) | ✅ UI displayed *"Your document is already optimally compressed"* and `0% (Optimal)` |
| **Non-PDF Rejection** | `non_pdf_file.txt` (37 B) | Error alert banner | ✅ Rejected with: *"Skipped non-PDF file: non_pdf_file.txt"* |
| **Corrupted PDF Rejection** | `corrupted_file.pdf` (34 B) | Error alert banner | ✅ Rejected with: *"corrupted or not a valid PDF"* |
| **Regression Checks** | `/merge` and `/split` pages | Navigation & Layout verified | ✅ Both tools operational without regressions |
| **Console Errors** | Entire workflow | 0 console errors logged | ✅ Clean browser runtime execution |

---

## Rotate PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pypdf` (BSD-3-Clause permissive license).
  - Lossless rotation: adjusts page dictionary `/Rotate` attributes without recompressing streams, degrading vector curves, or re-encoding bitmaps.
- **Rotation Angles**:
  - `90°`: Clockwise quarter-turn.
  - `180°`: Half-turn upside-down inversion.
  - `270°`: Clockwise 3/4 turn (90° counter-clockwise).
- **Scope Options**:
  - All pages: Rotates entire document.
  - Selective pages / ranges: Allows targeting specific pages (e.g. `1, 3` or `2-4`) while leaving other pages in original orientation.
- **UI & UX**: Responsive Next.js page at `/rotate` with drag-and-drop dropzone, angle selection buttons, scope toggle, real-time progress indicator, secure download button, and auto-dismissing error alerts.

---

## Live Browser Verification Results — Rotate PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **90° All Pages** | `rotate_test_multipage.pdf` (3 pages) | `rotated_90.pdf` | ✅ Downloaded, inspected with pypdf: all 3 pages rotated to 90° |
| **180° All Pages** | `rotate_test_multipage.pdf` (3 pages) | `rotated_180.pdf` | ✅ Downloaded, inspected with pypdf: all 3 pages rotated to 180° |
| **270° All Pages** | `rotate_test_multipage.pdf` (3 pages) | `rotated_270.pdf` | ✅ Downloaded, inspected with pypdf: all 3 pages rotated to 270° |
| **Selective Pages (1, 3)** | `rotate_test_multipage.pdf` (3 pages) | `rotated_selective.pdf` | ✅ Downloaded: Page 1=90°, Page 2=0°, Page 3=90° (page 2 unchanged) |
| **Non-PDF Rejection** | `rotate_non_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: rotate_non_pdf.txt"* |
| **Corrupted PDF** | `rotate_corrupted.pdf` | Worker error banner | ✅ Server error: *"corrupted or not a valid PDF: Stream has ended unexpectedly"* |
| **Encrypted PDF** | `rotate_encrypted.pdf` | Worker error banner | ✅ Server error: *"password-protected and cannot be rotated"* |
| **Out-of-Bounds Range** | Range `10-20` on 3-page doc | Error banner | ✅ Validation error: *"Range '10-20' exceeds total pages in document (3)"* |
| **Regression Checks** | `/merge`, `/split`, `/compress` | Headings verified | ✅ All 3 tools loaded and fully functional |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Watermark PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `reportlab` (BSD License) + `pypdf` (BSD-3-Clause). Both are fully permissive and commercially friendly.
  - In-memory vector canvas overlay with exact matching page dimensions merged via `pypdf.PageObject.merge_page(..., over=True)`.
- **Customizable Attributes**:
  - Text: Customizable text (up to 200 chars).
  - Positions: `diagonal` (center rotated to page diagonal aspect ratio or 45°), `center`, `top` (header), `bottom` (footer).
  - Angle: -360° to 360° (default 45° for diagonal, 0° for horizontal).
  - Font Size: 8px to 144px (default 48px).
  - Opacity: 5% to 100% (default 30%).
  - Color: Hex RGB string (e.g. Red `#DC2626`, Dark Gray `#1F2937`, Blue `#2563EB`).
  - Scope: All pages vs Selected pages (e.g. `1, 3` or `2-4`).
- **UI & UX**: Responsive Next.js page at `/watermark` with live styling inputs, preset buttons, scope toggle, progress bar, direct download from MinIO, and error handling.

---

## Live Browser Verification Results — Watermark PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Diagonal All Pages** | `rotate_test_multipage.pdf` (3 pages) | `watermarked_diagonal.pdf` | ✅ Downloaded, inspected with pypdf: all 3 pages stamped with `"TOP SECRET"` |
| **Exact Center** | `rotate_test_multipage.pdf` (3 pages) | `watermarked_center.pdf` | ✅ Downloaded, inspected with pypdf: all 3 pages stamped with `"DRAFT COPY"` |
| **Selective Pages (1, 3)** | `rotate_test_multipage.pdf` (3 pages) | `watermarked_selective.pdf` | ✅ Downloaded: Page 1=Stamped, Page 2=Clean, Page 3=Stamped (`"INTERNAL ONLY"`) |
| **Non-PDF Rejection** | `rotate_non_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: rotate_non_pdf.txt"* |
| **Corrupted PDF** | `rotate_corrupted.pdf` | Worker error banner | ✅ Server error: *"corrupted or not a valid PDF: Stream has ended unexpectedly"* |
| **Encrypted PDF** | `rotate_encrypted.pdf` | Worker error banner | ✅ Server error: *"password-protected and cannot be watermarked"* |
| **Out-of-Bounds Range** | Range `10-20` on 3-page doc | Error banner | ✅ Validation error: *"Range '10-20' exceeds total pages in document (3)"* |
| **Regression Checks** | `/merge`, `/split`, `/compress`, `/rotate` | Headings verified | ✅ All 4 tools loaded and operational without regressions |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Add Page Numbers Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `reportlab` (BSD License) for vector canvas text overlays with exact typography and positioning.
  - `pypdf` (BSD-3-Clause) for PDF parsing, page dimension extraction, content merging, and writeout.
  - Commercial license safe and strictly compatible.
- **Placement & Rotation Normalization**:
  - 6 positions supported: `top_left`, `top_center`, `top_right`, `bottom_left`, `bottom_center`, `bottom_right`.
  - Stamping on rotated pages is normalized via `page.transfer_rotation_to_content()`, preserving visual orientation and correctly orienting numbers regardless of page rotation (90°, 180°, 270°) or mixed page sizes (Letter, A4, Landscape).
- **Numbering Formats & Configuration**:
  - Formats: `page_n_of_total` ("Page 1 of 10"), `page_n` ("Page 1"), `n` ("1"), and `n_of_total` ("1 of 10").
  - Starting page offset (`start_page`) allowing clean cover pages.
  - Starting number offset (`start_number`) allowing continued sequence from previous volumes.
  - Font size (8 to 36 pt), margins (10 to 100 pt), and custom text colors (hex / color picker).
- **UI & UX**: Responsive Next.js page at `/page-numbers` with live interactive visual page preview, position selector buttons, format cards, numeric inputs, color pickers, progress bar, direct download from MinIO, and error handling.

---

## Live Browser Verification Results — Page Numbers PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Top Right Numbering** | `sample_3page.pdf` (3 pages) | `e2e_numbered_test.pdf` | ✅ Downloaded, inspected with pypdf: Page 1=Clean (start_page 2), Page 2="Page 1 of 2", Page 3="Page 2 of 2" |
| **Non-PDF Rejection** | `not_a_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: not_a_pdf.txt. Only PDF files are supported."* |
| **Corrupted PDF** | `corrupt.pdf` | Worker error banner | ✅ Server error: *"File content is not a valid PDF document (missing %PDF- header signature)"* |
| **Encrypted PDF** | `sample_encrypted.pdf` | Worker error banner | ✅ Server error: *"File 'sample_encrypted.pdf' is password-protected and cannot be processed."* |
| **Regression Checks** | `/merge`, `/split`, `/compress`, `/rotate`, `/watermark` | Verified | ✅ All 5 prior tools remain fully functional and tested |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Protect PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pypdf` (BSD-3-Clause) + `cryptography` (Apache 2.0 / BSD) providing standard AES-256 PDF encryption.
  - Verification: `pypdf` encrypts using `algorithm="AES-256"` (Standard Security Handler Revision 5/6 compatible). Opening without the password or with an invalid password fails cleanly.
- **Strict Security Architecture**:
  - **Zero Database Password Leaks**: When `/jobs/{id}/start` is called, `password` and `confirm_password` are stripped from `payload.config` before committing to PostgreSQL `jobs.config`.
  - **Ephemeral In-Memory Secret Passing**: The password is stored in Redis under an isolated ephemeral key (`ephemeral_job_password:{job_id}`) with a 300-second TTL.
  - **Single-Use Consumption & Memory Wiping**: When the Celery worker task runs, it retrieves the secret, immediately deletes the Redis key, injects it into memory for the handler, and wipes in-memory references upon completion.
  - **Zero Result Metadata Leaks**: The PostgreSQL `jobs.result_file` stores only `is_encrypted: True` and `encryption_algorithm: "AES-256"`.
  - **DRM Advisory**: The UI informs users that PDF password protection enforces standard viewer decryption but is not equivalent to centralized DRM systems.
- **UI & UX**: Responsive Next.js page at `/protect` with password and confirm-password fields, show/hide eye toggles, password match status indicator, clear security notices, progress bar, and direct download.

---

## Live Browser Verification Results — Protect PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **AES-256 Encryption** | `sample_3page.pdf` (3 pages) | `e2e_protected_test.pdf` | ✅ Downloaded: `is_encrypted: True`. Correct password (`SuperSecret2026!`) unlocked 3 pages. Wrong password rejected. |
| **Password Mismatch** | Mismatched input | Warning alert | ✅ Client indicator displayed: *"Passwords do not match"* and prevented submission |
| **Show/Hide Visibility** | Eye toggle button | Input toggled type | ✅ Password field type toggled between `password` and `text` |
| **Non-PDF Rejection** | `not_a_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: not_a_pdf.txt. Only PDF files are supported."* |
| **Corrupted PDF** | `corrupt.pdf` | Worker error banner | ✅ Server error: *"File content is not a valid PDF document (missing %PDF- header signature)"* |
| **Already-Encrypted PDF** | `sample_encrypted.pdf` | Worker error banner | ✅ Server error: *"File 'sample_encrypted.pdf' is already password-protected."* |
| **Database Audit** | PostgreSQL records | 0 passwords stored | ✅ Verified zero passwords in PostgreSQL `jobs.config` or `jobs.result_file` |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Unlock PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pypdf` (BSD-3-Clause permissive license).
  - Verifies user password against encryption dictionary, decrypts document streams, extracts all pages and metadata, and writes an unencrypted output PDF (`is_encrypted: False`).
  - No brute-forcing, password cracking, or unauthorized bypass attempted; requires valid document credentials.
- **Security & Ephemeral Secrets**:
  - **Zero Database Persistence**: The user-supplied password is stripped from `jobs.config` in PostgreSQL and NEVER written to disk or audit logs.
  - **Ephemeral Redis Storage**: Stored exclusively in Redis under `ephemeral_job_password:{job_id}` with a 300-second TTL.
  - **Single-Use Worker Retrieval**: Retrieved by Celery worker upon task initialization, immediately deleted from Redis, injected into memory, and purged after handler completion (`del password`, `worker_config["password"] = None`).
  - **Sanitized Result Metadata**: Result dictionary returns `is_encrypted: False` and never exposes the password.
- **Validation & Error Handling**:
  - `NOT_ENCRYPTED`: Rejects files that are already unencrypted with a clear explanation that unlocking is unnecessary.
  - `INCORRECT_PASSWORD`: Rejects invalid passwords with a user-friendly error prompt.
  - `INVALID_PASSWORD`: Enforces non-empty string and maximum length limit (128 chars).
  - `CORRUPTED_FILE` / `EMPTY_INPUT_FILE`: Handles malformed PDFs and 0-byte uploads safely.
- **UI & UX**: Responsive Next.js page at `/unlock` with file dropzone, password input with show/hide toggle, output filename override, authorized decryption security notice, real-time progress bar, success summary card with "Unrestricted" badge, and direct download.

---

## Live Browser Verification Results — Unlock PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Decryption & Unlock** | `unlock_test_locked.pdf` (AES-256, 3 pages) | `e2e_unlocked_result.pdf` | ✅ Downloaded: `is_encrypted: False`, 3 pages intact (450x650), opens freely without password, title metadata preserved |
| **Incorrect Password** | Supplied `WrongPasswordAttempt999` | Error banner | ✅ Server error: *"The password provided is incorrect."* displayed in `#global-error-banner` |
| **Unencrypted Rejection** | Uploaded `sample_3page.pdf` | Error banner | ✅ Server error: *"File 'sample_3page.pdf' is not password-protected and does not need to be unlocked."* |
| **Non-PDF Rejection** | `not_a_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: not_a_pdf.txt. Only PDF files are supported."* |
| **Show/Hide Visibility** | Eye toggle button | Input toggled type | ✅ Password field type toggled between `password` and `text` |
| **File Reset** | Clicked "Change File" | Returned to dropzone | ✅ Cleared previous file and restored file picker button |
| **Regression Checks** | Protect, Merge, Page Numbers | All operational | ✅ Ran browser tests for Protect, Merge, and Page Numbers; all passed |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Extract Pages Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pypdf` (BSD-3-Clause permissive license).
  - Extracts selected pages and page ranges from a source PDF and compiles them into a single, unified output PDF document.
  - Strict preservation of original page dimensions, aspect ratios, orientations (`/Rotate`), vector art, fonts, and object streams.
- **Extraction Capabilities**:
  - **Individual Pages**: e.g. `1, 3, 5` extracts exactly those pages.
  - **Sequential Ranges**: e.g. `2-4` extracts pages 2, 3, and 4.
  - **Custom Non-Sequential Ordering**: e.g. `4, 2-3, 1` extracts page 4, then page 2, then page 3, then page 1.
  - **Overlapping / Duplicate Pages**: e.g. `2, 2-3` repeats requested pages in the exact specified order.
  - **Extract All Pages Mode**: Option to extract all pages `1..N` into a single organized PDF.
- **Validation & Safe Error Handling**:
  - `PAGE_RANGE_OUT_OF_BOUNDS`: Rejects page numbers higher than total page count or less than 1.
  - `INVALID_PAGE_RANGE`: Rejects inverted ranges (e.g. `5-2`), non-numeric characters, or empty specifications.
  - `ENCRYPTED_FILE`: Rejects password-protected PDFs with a clear notice.
  - `CORRUPTED_FILE` / `EMPTY_INPUT_FILE`: Safely rejects malformed or 0-byte PDFs.
- **UI & UX**: Responsive Next.js page at `/extract-pages` with file dropzone, automatic page count detection badge, mode switcher between specific ranges and all pages, preset chips, custom output filename override, real-time progress bar, success summary card, and direct download.

---

## Live Browser Verification Results — Extract Pages (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Custom Ordering & Ranges** | `browser_sample_5page.pdf` (5 pages) with range `4, 2-3, 1` | `browser_extracted_custom.pdf` (4 pages) | ✅ Downloaded: exactly 4 pages in order (Page 4: 350x450, Page 2: 250x350, Page 3: 300x400, Page 1: 200x300) |
| **Extract All Pages Mode** | `browser_sample_5page.pdf` (5 pages) with Extract All toggle | `browser_all_pages.pdf` (5 pages) | ✅ Downloaded: all 5 pages extracted into unified PDF |
| **Out-of-Bounds Rejection** | Supplied range `1, 8` on 5-page doc | Error banner | ✅ Client validation alert: *"Page 8 is out of bounds for a document with 5 pages."* |
| **Non-PDF Rejection** | `not_a_pdf.txt` | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: not_a_pdf.txt. Only PDF files are supported."* |
| **Encrypted Rejection** | `sample_encrypted.pdf` | Worker error banner | ✅ Server error: *"File 'sample_encrypted.pdf' is password-protected and cannot be processed."* |
| **Reset Selection** | Clicked "Extract More Pages" / "Change File" | Returned to dropzone | ✅ Cleared previous file and restored file picker button |
| **Regression Checks** | Protect, Unlock, Page Numbers, Merge | All operational | ✅ Ran live browser tests for Protect, Unlock, Page Numbers, and Merge; all passed |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## Organize PDF Feature Details (Milestone 2)

- **Engine & Licensing**:
  - `pypdf` (BSD-3-Clause permissive license).
  - Visual page-level manipulation: allows arbitrary reordering, per-page 90° clockwise rotation increments, page duplication, and page deletion.
  - Strict preservation of original page dimensions, aspect ratios, orientations, content, and document metadata (Title, Author, Subject).
- **Interactive Capabilities**:
  - **Visual Thumbnails**: Rendered via client-side PDF.js canvas with graceful document wireframe fallback.
  - **Drag-and-Drop Reordering**: Intuitive drag-and-drop card grid with drag-over indicator and keyboard/touch Move Left / Move Right buttons.
  - **Per-Page Rotation**: 90° clockwise increment rotations displayed with visual rotation tags and rotated preview images.
  - **Duplication & Deletion**: Clone any page immediately adjacent; delete unwanted pages (with minimum 1-page guardrail).
  - **Undo & Reset Controls**: Complete history stack for undoing modifications and single-click reset to original uploaded document.
  - **Batch Selection**: Select / Deselect All, Batch Rotate Selected, Batch Delete Selected.
- **Validation & Safe Error Handling**:
  - `PAGE_RANGE_OUT_OF_BOUNDS`: Rejects invalid page index references.
  - `INVALID_ROTATION_ANGLE`: Enforces 90° increments.
  - `ENCRYPTED_FILE`: Rejects password-protected PDFs with informative error banner.
  - `CORRUPTED_FILE` / `EMPTY_INPUT_FILE`: Safely rejects malformed or 0-byte PDFs.
- **UI & UX**: Responsive Next.js page at `/organize-pdf` with drag-and-drop dropzone, interactive page card grid, global toolbar, custom output filename override, live progress bar, and direct download button.

---

## Live Browser Verification Results — Organize PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Visual Loading** | 4-page PDF with distinct dimensions | 4 visual page cards rendered | ✅ Grid rendered cards #1..#4 with page numbers and dimensions |
| **Per-Page Rotate** | Clicked rotate on Page 1 | `+90°` badge displayed | ✅ Page card rotated 90° clockwise visually |
| **Page Duplication** | Clicked duplicate on Page 2 | 5 page cards | ✅ Page 2 duplicated as adjacent card; total count increased to 5 |
| **Page Deletion** | Clicked delete on Page 4 | 4 page cards | ✅ Page 4 deleted; total count decreased to 4 |
| **Undo Action** | Clicked Undo button | 5 page cards | ✅ Deleted page restored from history stack |
| **Reset to Original** | Clicked Reset button | 4 page cards, 0° rotation | ✅ Reverted all changes to initial 4 pages |
| **Output Compilation** | Final edits: P1 (+90°), P3 dup, P3 copy (+180°), P2 deleted | Single organized PDF | ✅ Downloaded: exactly 4 pages matching specified order, dimensions, rotations, and metadata |
| **Non-PDF Rejection** | `.txt` file | Error banner | ✅ Client validation alert: *"Skipped non-PDF file: ... Only PDF files are supported."* |
| **Tool Card on Home** | Navigated to `/` | Card visible | ✅ "Organize PDF" card present in grid and links directly to `/organize-pdf` |
| **Regression Checks** | All 10 tool routes | All 200 OK | ✅ Checked `/merge`, `/split`, `/compress`, `/rotate`, `/watermark`, `/page-numbers`, `/protect`, `/unlock`, `/extract-pages`, `/organize-pdf` |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean runtime execution |

---

## PDF.js Security Hardening & Audit Verification

- **Version Upgrade**: Upgraded `pdfjs-dist` to the latest stable release **`6.4.299`** (addressing all historical security advisories including CVE-2024-4367 and architectural sandbox exploits).
- **Local Worker Bundling**: Removed external CDN loading (`cdnjs.cloudflare.com`). Bundled and served `/public/pdf.worker.min.mjs` locally matching `pdfjs-dist@6.4.299` (1.26 MB).
- **Parser Security Options & Breaking Changes**:
  - In PDF.js 6.x, `isEvalSupported` has been removed from the parser because dynamic JavaScript eval was completely eliminated from the engine codebase following CVE-2024-4367; retained runtime safety parameter as a defense-in-depth measure.
  - `enableXfa: false` explicitly configured to prevent XML Forms Architecture execution.
  - `page.render({ canvas, canvasContext: ctx, viewport })` updated to supply the required DOM `canvas` object per PDF.js 6.x `RenderParameters` specifications.
  - `disableRange: true`, `disableStream: true`, `disableAutoFetch: true` configured for direct memory buffer parsing.
  - Cloned buffer copy `arrayBuffer.slice(0)` passed to Web Worker to protect the original ArrayBuffer from thread transferable object detaching.
- **Privacy Verification**:
  - Thumbnail generation is executed 100% locally in browser memory via HTML5 `<canvas>` without sending PDF contents or byte streams to external services.
- **Compressed Object Streams & Metadata**:
  - Maintained `/ObjStm` page-count detection heuristic and `test_extract_pages_metadata_preservation` / `test_organize_preserves_metadata`.
- **npm audit Results & Advisory Analysis**:
  - `npm audit --omit=dev`: **0 vulnerabilities** (0 critical, 0 high, 0 moderate, 0 low). Production runtime dependencies are completely clean.
  - Development-only advisories: 5 high advisories stemming from a single transitive dependency `braces <= 3.0.3` (GHSA-vfj7-8cjw-p6xm, DoS via deeply nested patterns) pulled via `@next/eslint-plugin-next -> fast-glob -> micromatch -> braces`. No fixed release exists on npm (`3.0.3` is latest). Forcing a downgrade to `eslint-config-next@14.2.35` would break compatibility with Next.js 16.4.0, React 19.3.0, and ESLint 9. This dependency is strictly build/lint-time and never bundled or executed at runtime.

---

## PDF to JPG Feature Details (Milestone 2)

- **Engine & Permissive Licensing**:
  - `pypdfium2` (v5.14.0, dual-licensed BSD-3-Clause / Apache-2.0, wrapping Google PDFium).
  - Pre-compiled standalone binaries bundled with zero external system libraries (no Poppler or Ghostscript AGPL requirements).
  - `Pillow` (HPND / Permissive) for JPEG encoding, subsampling, and optimization.
- **Local & Private Rendering**:
  - PDF rendering executes 100% locally within DocForge's own backend Celery worker containers.
  - Zero external APIs or cloud conversion services are called.
- **Resolution & Quality Tiers**:
  - **Standard (150 DPI)**: Default sensible resolution for general viewing, web embedding, and office documents (`scale = 150 / 72.0 = 2.0833`).
  - **High (300 DPI)**: Print-ready resolution for crisp typography and artwork reproduction (`scale = 300 / 72.0 = 4.1667`).
  - **JPEG Quality**: Standard (85%) or Maximum (95%) with progressive encoding and RGB normalization.
- **Packaging & Delivery**:
  - Each page rendered as an individual sequential JPEG image: `page_01.jpg`, `page_02.jpg`, etc.
  - Output packaged into a standard ZIP archive with SHA256 checksum calculation and custom filename support.
- **Resource Limits & Memory Safeguards (Audited & Enforced)**:
  - **Upload Size Limit**: Configurable `PDF_TO_JPG_MAX_FILE_SIZE_MB: 50` (enforced at API registration, direct upload, and worker handler levels with 413 `FILE_TOO_LARGE`). Client-side validation blocks uploads > 50 MB before transfer.
  - **Sensible Page Count Limits**:
    - Standard resolution (<= 150 DPI): `PDF_TO_JPG_MAX_PAGES_DEFAULT: 100` pages.
    - High resolution (> 150 DPI / 300 DPI): `PDF_TO_JPG_MAX_PAGES_300_DPI: 50` pages.
    - Requests exceeding limits return 400 `EXCESSIVE_PAGE_COUNT` with explicit error guidance.
  - **Rendering Dimension & Pixel Limits**:
    - `PDF_TO_JPG_MAX_RENDER_DIMENSION: 8000` px (max width or height).
    - `PDF_TO_JPG_MAX_RENDER_PIXELS: 36_000_000` pixels (~36 Megapixels).
    - Inspects page dimensions in points (`page.get_size()`) and rejects extreme dimensions prior to memory buffer allocation with 400 `PAGE_DIMENSIONS_TOO_LARGE`.
  - **Aggregate Output & Workspace Limit**:
    - Configurable `PDF_TO_JPG_MAX_AGGREGATE_OUTPUT_MB: 250` MB.
    - Evaluated incrementally as each page JPEG is rendered and written to the ZIP stream.
    - If total generated image bytes or ZIP size exceeds 250 MB, the job aborts immediately with 413 `OUTPUT_SIZE_LIMIT_EXCEEDED`, partial ZIP artifacts are removed from disk, PDFium handles are closed, and temporary workspace is deleted cleanly.
  - **Incremental Processing & Guaranteed Cleanup**:
    - Pages are rendered, encoded to JPEG, and written directly into the ZIP archive stream one at a time.
    - Native `bitmap.close()`, `page.close()`, and `doc.close()` are strictly guarded by nested `try ... finally` blocks.
    - Temporary directories are cleaned up immediately on both success and failure with zero Windows file lock conflicts (`WinError 32`).

---

## Live Browser Verification Results — PDF to JPG (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Non-PDF Rejection** | `not_a_pdf.txt` | Error banner | ✅ Client alert: *"Skipped non-PDF file: not_a_pdf.txt. Only PDF files are supported."* |
| **Page Count Detection** | 3-page PDF | Detected badge | ✅ Badge displayed: *"3 pages detected"* |
| **300 DPI High Resolution** | 3-page PDF | 300 DPI card selected | ✅ Resolution updated in job config payload |
| **95% Maximum Quality** | Quality toggle | Maximum selected | ✅ Quality indicator updated to 95% |
| **Custom ZIP Name** | `browser_e2e_gallery.zip` | Config applied | ✅ Custom output name set and persisted |
| **Celery Processing** | 3-page PDF | Status 100% | ✅ Processed via Celery worker into ZIP archive |
| **Summary Display** | Conversion result | Stats cards | ✅ Result summary verified: "3 Pages", "300 DPI" |
| **ZIP Download & Verification** | Downloaded `.zip` | Valid archive | ✅ Downloaded: 3 JPEG files (`page_01.jpg`..`03.jpg`) with matching 300 DPI pixel dimensions (833x1250, 1042x1458, 1250x1667) |
| **Home Tool Card** | Homepage `/` | "PDF to JPG" card | ✅ Visible in tools grid and links directly to `/pdf-to-jpg` |
| **Regression Checks** | All 11 tool routes | All 200 OK | ✅ Checked `/merge`, `/split`, `/compress`, `/rotate`, `/watermark`, `/page-numbers`, `/protect`, `/unlock`, `/extract-pages`, `/organize-pdf`, `/pdf-to-jpg` |
| **Console Errors** | Entire workflow | 0 console errors | ✅ Clean browser runtime execution |

---

## JPG to PDF Feature Details (Part 16)

- **Engine & Licensing**:
  - `reportlab` (BSD-3-Clause) for PDF canvas layout, vector/bitmap rendering, page dimensions, and embedding JPEG streams.
  - `Pillow` (HPND / Permissive) for JPEG decoding, validation, dimension inspection, and EXIF orientation normalization.
  - 100% local processing within DocForge's own infrastructure (zero external services).
- **Features**:
  - Multiple JPG/JPEG upload support (up to 50 files per job).
  - Visual image gallery with thumbnails, image dimensions, file sizes, and page number badges.
  - Drag-and-drop reordering between image cards, plus accessible move earlier/later buttons.
  - Per-image removal and clear all functionality.
  - Orientation options: `Automatic` (adapts page to image ratio), `Portrait` (vertical), and `Landscape` (horizontal).
  - Page size options: `Fit to Image` (exact image dimension), `A4` (210 x 297 mm), and `US Letter` (8.5 x 11 in).
  - Margins: `No Margin` (0 pt), `Small Margin` (18 pt / 0.25 in), and `Normal Margin` (36 pt / 0.50 in).
  - Custom output PDF filename configuration.
  - Real-time upload and processing progress bar, completion summary, and direct download button.
- **Configurable Resource Limits**:
  - `JPG_TO_PDF_MAX_FILE_SIZE_MB: 25` (max size per input image).
  - `JPG_TO_PDF_MAX_FILES: 50` (max image files per conversion job).
  - `JPG_TO_PDF_MAX_IMAGE_DIMENSION: 10000` (max width or height in px per image).
  - `JPG_TO_PDF_MAX_TOTAL_PIXELS: 150_000_000` (max cumulative pixels across all images to prevent image decompression bombs).
  - `JPG_TO_PDF_MAX_OUTPUT_PDF_MB: 100` (max aggregate generated PDF size).
  - Strict cleanup of all image handles and partial output files on success and failure.

---

## Live Browser Verification Results — JPG to PDF (Edge / Chromium)

| Scenario | Input | Actual Result | Verification |
|---|---|---|---|
| **Multi-Image Upload & Reordering** | 3 distinct JPEGs (`photo_red`, `photo_green`, `photo_blue`) | Gallery displayed 3 thumbnails; reordered green earlier | ✅ UI cards displayed `#1`, `#2`, `#3` in updated order |
| **A4 Landscape with Small Margin** | 3 images, Landscape orientation, A4 size, Small margin | Generated `vacation_album.pdf` | ✅ Downloaded, opened with `pypdf`: 3 pages, Landscape A4 dimensions (841.89 x 595.28 pt) |
| **Non-JPG File Rejection** | `not_a_jpg.txt` | Error banner | ✅ Rejected with: *"Only JPG/JPEG images are accepted. Skipped: not_a_jpg.txt"* |
| **All 12 Tool Regressions** | `/merge`, `/split`, `/compress`, `/rotate`, `/watermark`, `/page-numbers`, `/protect`, `/unlock`, `/extract-pages`, `/organize-pdf`, `/pdf-to-jpg`, `/jpg-to-pdf` | All 12 routes healthy (200 OK) | ✅ All pages rendered without errors or regressions |
| **Console Errors** | Entire workflow | 0 console errors logged | ✅ Clean browser runtime execution |

---

## Part 17 Feature Details — All Tools Directory, Theme System & Real-Time Job Progress

- **All Tools Directory (`/tools`)**:
  - Live client-side search across tool title, description, category, and alias keywords.
  - Category filter pills: `All`, `Organize`, `Optimize`, `Convert`, `Security`.
  - Active tool count badge and keyboard shortcut indicator (`/` to focus search).
  - Empty state with search query display and one-click "Clear search" reset button.
  - 12 tool cards with icon, title, description, category badge, and direct links.
  - Fully responsive with mobile navigation drawer.

- **Theme System (Dark/Light)**:
  - System preference detection via `window.matchMedia('(prefers-color-scheme: dark)')` with dynamic listener.
  - Explicit user preference toggle: `light`, `dark`, or `system`.
  - Persistent storage in `localStorage` under key `docforge-theme`.
  - Zero-FOUC (Flash of Unstyled Content) inline script in `<head>` applying `.dark` class before DOM render.
  - Consistent theming applied to homepage, `/tools` directory, all 12 tool routes, navbar, dropzones, error pages, and modal elements.

- **Real-Time Job Progress (Server-Sent Events)**:
  - Backend endpoint `GET /api/v1/jobs/{id}/progress` using FastAPI `StreamingResponse` with `media_type="text/event-stream"`.
  - Redis Pub/Sub channel per job (`job:progress:{job_id}`).
  - Immediate yield of initial DB status upon connection to avoid waiting for the first worker event.
  - Periodic SSE heartbeat comments (`: heartbeat\n\n`) every 15 seconds to keep intermediary proxies and mobile connections alive.
  - Client disconnect detection via `await request.is_disconnected()` with guaranteed Redis unsubscription and listener cleanup.
  - Terminal events (`COMPLETED`, `FAILED`, `CANCELLED`) sent with progress=100 and clean generator termination.
  - Frontend `useJobProgress` React hook with resilient auto-reconnect and automatic HTTP polling fallback if SSE encounters network failure or is unsupported.

- **Branded Error Pages**:
  - Branded 404 Not Found page (`frontend/src/app/not-found.tsx`).
  - Branded 500 Internal Error boundary (`frontend/src/app/error.tsx`) with recovery retry button.
  - Root-level global error boundary (`frontend/src/app/global-error.tsx`).

---

## Live Browser Verification Results — Part 17 (Edge / Chromium)

| Scenario | Input / Action | Actual Result | Verification |
|---|---|---|---|
| **Tools Directory Search** | Typed `"convert"` in `/tools` search input | Filtered down to 2 tools (`PDF to JPG` and `JPG to PDF`) | ✅ Count updated to "2 of 12 tools" |
| **Category Filter** | Clicked `"Security"` category pill | Filtered down to 2 tools (`Protect PDF` and `Unlock PDF`) | ✅ Count updated to "2 of 12 tools" |
| **Empty Search State** | Typed `"nonexistent tool"` | Rendered empty state with "No tools found" | ✅ Clicking "Clear search" restored all 12 tools |
| **Dark Theme Toggle** | Clicked `#theme-toggle-btn` | `<html>` gained class `dark`; background transitioned to dark slate | ✅ Persisted in `localStorage.getItem("docforge-theme")` |
| **Theme Persistence across routes** | Navigated from `/tools` to `/merge` | Theme remained dark without flash | ✅ Document class and background preserved |
| **SSE Real-Time Progress Stream** | Created real job via API, connected to SSE endpoint | Received initial status event, heartbeat, and terminal completion event | ✅ Streamed cleanly over `text/event-stream` |
| **All 12 Tool Regressions** | Navigated to all 12 tool routes with theme toggle | All 12 routes healthy (200 OK) | ✅ Zero regressions across all tool pages |
| **Console Errors** | Entire workflow execution | 0 console errors logged | ✅ Clean browser runtime execution |

---

## Live Browser Verification Results — Part 19 Security & Regressions (Edge / Chromium)

| Scenario | Input / Action | Actual Result | Verification |
|---|---|---|---|
| **Security Headers & CSP Verification** | Navigated to `/merge` and `/tools` on production Next.js build | Verified `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, and `Permissions-Policy` | ✅ Headers present and enforced |
| **CSP Script & Worker Compatibility** | Evaluated inline theme script and PDF.js worker execution | Theme applied without inline-script blockage; Web Worker instantiated cleanly (`worker-src 'self' blob:`) | ✅ Zero CSP violation reports |
| **All 12 Tool Regressions** | Navigated across all 12 tool routes with security headers active | All 12 routes healthy (200 OK), drag-and-drop dropzones interactive | ✅ Zero regressions across all tool pages |
| **Console Errors** | Inspected browser developer console during navigation and interactions | 0 console errors or warnings logged | ✅ Clean browser runtime execution |

---

## Live Browser Verification Results — Tool Header UI Consistency (Edge / Chromium)

| Scenario | Input / Action | Actual Result | Verification |
|---|---|---|---|
| **Unified Tool Header Component** | Navigated across all 12 tool pages (`/merge`, `/split`, `/compress`, `/rotate`, `/watermark`, `/page-numbers`, `/protect`, `/unlock`, `/extract-pages`, `/organize-pdf`, `/pdf-to-jpg`, `/jpg-to-pdf`) | Every tool renders identical 64px (`h-16`) sticky header with glassmorphism backdrop blur, Back link, tool-specific icon container (`w-9 h-9`), high-contrast title, "DocForge Tools" badge, outline action buttons (`All Tools`, `Dashboard`), and `ThemeToggle` | ✅ 100% visual consistency across all 12 tools |
| **Back Navigation Behavior** | Navigated `/tools` -> `/rotate` -> clicked `Back` control | Browser history `window.history.back()` returned user directly to `/tools`; fallback href (`/`) preserved for direct landings | ✅ Seamless SPA history and fallback navigation |
| **Mobile Responsiveness (375x812)** | Rendered on 375px mobile viewport | Responsive header collapses text to icon buttons, hides badge cleanly to prevent overlap, 0 horizontal overflow (`scrollWidth <= clientWidth`) | ✅ Clean mobile layout |
| **Theme System Integration** | Toggled theme via `#theme-toggle-btn` in header on light and dark | Seamless transition, crisp dark/light borders and glassmorphism styling | ✅ Zero FOUC, theme state persisted |
| **Console Errors** | Inspected browser developer console across all navigation routes | 0 console errors logged | ✅ Clean runtime execution |

---

## Automated Test Verification
 
| Test Suite | Result | Details |
|---|---|---|
| **Backend Unit & Integration Tests** | ✅ **181 passed, 0 failed** | Pytest: state machine, storage, handlers (all 13 tools including Repair PDF), resource limits, failure cleanup, Celery worker + MinIO integration, SSE reliability, Part 19 security tests, Part 20 production health & monitoring tests, and 10 dedicated Part 22 Repair PDF tests (`test_repair_handler.py` and `test_repair_integration.py`) |
| **Frontend Unit & Integration Tests** | ✅ **132 passed, 0 failed** | Vitest: 20 test files (all 13 tools including Repair PDF, Home, `/tools` directory, `ThemeToggle`, `useJobProgress` hook, `tools-seo.test.ts`, `tool-header.test.tsx`, and `legal.test.tsx`) |
| **TypeScript Typecheck** | ✅ **0 errors** | `npx tsc --noEmit` clean across all components, configs, and pages |
| **npm audit** | ✅ **0 production vulnerabilities** | `npm audit --omit=dev` clean (0 vulnerabilities); 5 known development-dependency advisories from `eslint-config-next` / `braces` documented |
| **Next.js Production Build** | ✅ **Passed** | Clean compilation, static generation of all 23 routes including standalone output, dynamic `/sitemap.xml` (17 canonical routes), and `/robots.txt` |
| **Playwright Master E2E Suite** | ✅ **Passed (24 Scenarios)** | `tests/e2e/run_all.py` executing across 3 test suites in 87.81s: **Suite 1** All 13 PDF tools real end-to-end execution, configuration, and download verification (13/13 passed); **Suite 2** Edge cases & security (invalid uploads, corrupted PDF handling, encrypted file rejection, ClamAV malware rejection with HTTP 400 `MALWARE_DETECTED`, rate limit burst stability) (5/5 passed); **Suite 3** UX, SEO & Accessibility (theme persistence, navigation, 375px mobile responsiveness, robots.txt, sitemap.xml with 17 URLs, canonical tags, and **axe-core automated WCAG 2.1 AA audit with 0 violations across all 17 canonical routes in both light and dark modes**) (6/6 passed) |
| **Production Stack Dry-Run** | ✅ **Passed** | `verify_production_dryrun.py` against standard Docker Compose: 9 healthy containers, non-root users (`appuser` UID 10001, `nextjs` UID 1001), liveness/readiness 200, harmless PDF rotate 90 end-to-end, EICAR malware 400 rejection & purge, Redis rate limit 429, SSE progress stream, Sentry synthetic scrubbing, and 0 secrets/payloads in logs |

---

## Production Deployment Dry-Run Verification (Part 20)

| Check / Test Component | Result | Execution Details | Cloud Account / Production Prerequisites |
|---|---|---|---|
| **Multi-Stage Docker Images** | ✅ Verified | `docforge-backend:prod` (134 MB) & `docforge-frontend:prod` (88.7 MB) built without errors; pinned boto3/botocore dependencies | None (Runs locally) |
| **Non-Root User Execution** | ✅ Verified | Backend/Worker: `uid=10001(appuser)`; Frontend: `uid=1001(nextjs)` | None (Runs locally) |
| **Container Health & Compose Network** | ✅ Verified | All 9 containers healthy (`backend`, `frontend`, `worker`, `beat`, `postgres`, `redis`, `storage`, `clamav`, `proxy`) on isolated `internal-net` and `edge-net` | None (Standard Docker Compose) |
| **Liveness & Readiness Probes** | ✅ Verified | `/health/live` HTTP 200; `/health/ready` HTTP 200 with all 5 dependencies connected (DB, Redis, S3, Celery, ClamAV) | None |
| **Harmless PDF Job End-to-End** | ✅ Verified | Uploaded PDF via S3 presigned URL, scanned by ClamAV, executed by Celery worker (0.5s), downloaded via presigned URL, verified 90° rotation with `pikepdf` | None (Tested S3-compatible path locally) |
| **Malware Scanner Fail-Closed & EICAR** | ✅ Verified | Caught EICAR standard antivirus signature, returned HTTP 400 `MALWARE_DETECTED`, purged infected object from storage | None |
| **Redis-Backed Rate Limiter** | ✅ Verified | Burst of requests triggered HTTP 429 Too Many Requests with `Retry-After: 58s` | None |
| **SSE Real-Time Progress** | ✅ Verified | `GET /api/v1/jobs/{id}/progress` streamed `text/event-stream` with HTTP 200 | None |
| **Sentry Scrubber** | ✅ Verified | Scrubbed synthetic sensitive headers, passwords, secrets, PDF content, and presigned query params | None (Tested with synthetic payloads; live Sentry requires DSN) |
| **Log Privacy Audit** | ✅ Verified | Confirmed 0 passwords, credentials, tokens, presigned signatures, or raw PDF contents in container logs | None |
| **Cloudflare R2 Live Bucket** | ⏳ Pending Cloud Setup | S3-compatible path verified locally. Live Cloudflare R2 bucket requires real Cloudflare account & credentials | Real Cloudflare account & R2 API token required |
| **Production Domain & TLS** | ⏳ Pending Domain Setup | Caddy reverse proxy tested on local port 80/443. Live public domain & Let's Encrypt TLS require registered domain | Registered domain & DNS pointing to host required |

---

## Remaining Known Limitations & Operational Requirements

1. **ClamAV Memory Footprint**: The `clamav/clamav:latest` daemon requires ~1.0–1.2 GB of RAM to hold the virus definition database in memory. Production hosts must allocate sufficient memory or set `CLAMAV_ENABLED=False` / `CLAMAV_FAIL_CLOSED=False` only in constrained non-production testing environments.
2. **Fail-Closed Scanner Availability**: When `CLAMAV_FAIL_CLOSED=True` (default in production), any scanner network outage or daemon restart causes uploads to be rejected with HTTP 503 `SCANNER_UNAVAILABLE`. Monitor ClamAV daemon health alongside the web app.
3. **Digital Signatures**: Modifying document trees or extracting pages into bitmaps does not preserve cryptographic PDF signatures.
4. **Encrypted / Password-Protected PDFs**: Password-protected PDFs cannot be converted or repaired without decryption; users must unlock them first via `/unlock`.
5. **PDF Repair Recovery Limits**:
   - Repair reconstructs damaged cross-reference (`xref`) tables, trailers, missing `%%EOF` markers, and salvageable unreferenced streams.
   - It **cannot** invent or recreate completely destroyed, truncated, overwritten, or missing byte content (e.g. truncated content streams where text was never written).
   - In accordance with transparency standards, DocForge never falsely claims recovery of irrecoverably truncated content and returns HTTP 400 `UNRECOVERABLE_PDF`.
6. **Enforced Resource Boundaries**:
   - PDF Repair: 50 MB input file size limit, 1 file per job, single-document reconstruction.
   - PDF to JPG: 50 MB input, 100 pages at 150 DPI, 50 pages at 300 DPI, 8,000 px / 36 MP per page, 250 MB aggregate output limit.
   - JPG to PDF: 25 MB per image, 50 images per job, 10,000 px max dimension, 150 MP total pixels, 100 MB aggregate output PDF size.
   - Total Job Aggregate Upload Guard: 250 MB max aggregate payload across all files per job (`MAX_AGGREGATE_JOB_SIZE_MB`).
7. **Development Dependencies**: 5 high severity advisories in devDependencies (`eslint-config-next` / `micromatch` / `braces`), 0 vulnerabilities in production runtime dependencies (`npm audit --omit=dev` clean).
8. **Production Canonical Domain Configuration**: Set `NEXT_PUBLIC_SITE_URL` in production to configure canonical URLs, sitemaps, and robots.txt. Defaults safely to `https://docforge.com` with console build notice when unset.
9. **Cloudflare R2 Cloud Prerequisites**: Production deployment requires a real Cloudflare R2 account, bucket creation, and scoped API tokens as documented in `docs/deployment-guide.md`.
10. **Legal Customization Prior to Public Launch**: Customize deployer legal entity name, jurisdiction, governing law, and support contact email in `/privacy` and `/terms` prior to public hosting.

---

## Exact Next Development Task

**Part 23 — PDF to Word (DOCX) Conversion (`/pdf-to-word`)**:
- Engine: Permissive Python layout analysis & extraction library (`pdf2docx`).
- Next scheduled task after Part 22 completion. Do not start Part 23 until instructed.


