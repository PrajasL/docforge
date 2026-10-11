# File Processing Architecture

## 1. Overview

Every PDF tool in DocForge follows the same processing pipeline. Tool-specific logic is a plugin within a standardized framework. This ensures consistent behavior for upload, validation, processing, progress tracking, result storage, and cleanup across all tools.

---

## 2. Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    BASE PROCESSING PIPELINE                      │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │ 1. FETCH │──►│2. VALIDATE│──►│3. PROCESS│──►│ 4. FINALIZE │  │
│  │          │   │          │   │          │   │             │  │
│  │ Download │   │ File     │   │ Execute  │   │ Upload      │  │
│  │ inputs   │   │ integrity│   │ tool     │   │ result      │  │
│  │ from     │   │ check    │   │ logic    │   │ Update job  │  │
│  │ storage  │   │          │   │          │   │ Cleanup     │  │
│  └──────────┘   └──────────┘   └──────────┘   └─────────────┘  │
│       │              │              │               │            │
│       ▼              ▼              ▼               ▼            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  ERROR HANDLER                            │   │
│  │  - Catch exceptions                                       │   │
│  │  - Set job status to FAILED                               │   │
│  │  - Store error message + code                             │   │
│  │  - Clean up temp files                                    │   │
│  │  - Determine if retryable                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Fetch
- Download all input files from Object Storage to a temporary directory
- Temp directory is unique per job: `/tmp/docforge/jobs/{job_id}/`
- Verify file checksums match stored SHA-256 hashes

### Step 2: Validate
- Verify file type by reading magic bytes (not just extension)
- Verify file structure (is it a valid PDF?)
- Check for known malicious patterns (embedded JavaScript, suspicious actions)
- Verify file size matches metadata
- Check page count for tools that need it

### Step 3: Process
- Execute tool-specific logic (see Tool Handler section below)
- Report progress back to Redis for SSE streaming
- Respect timeout limits (soft timeout triggers graceful stop)

### Step 4: Finalize
- Upload result file(s) to Object Storage
- Calculate result file checksum
- Create output file record in database
- Update job status to COMPLETED
- Clean up temporary files

---

## 3. Tool Handler Interface

Every tool implements a standardized handler:

```python
# Conceptual interface — not actual code for implementation

class ToolHandler(Protocol):
    """Interface that every PDF tool must implement."""

    tool_id: str                    # e.g., "merge"
    display_name: str               # e.g., "Merge PDF"
    min_input_files: int            # Minimum files required
    max_input_files: int            # Maximum files accepted
    accepted_content_types: list    # e.g., ["application/pdf"]
    config_schema: dict             # JSON Schema for config validation

    def validate_config(self, config: dict) -> ValidationResult:
        """Validate tool-specific configuration."""
        ...

    def process(self, context: ProcessingContext) -> ProcessingResult:
        """Execute the tool's core logic."""
        ...

    def estimate_duration(self, files: list, config: dict) -> int:
        """Estimate processing time in seconds."""
        ...
```

### Processing Context
```python
class ProcessingContext:
    job_id: str
    input_files: list[InputFile]        # Local paths to downloaded files
    config: dict                         # Validated tool config
    output_dir: str                      # Directory for result files
    progress_callback: Callable          # Report progress (0-100)
    cancellation_token: CancellationToken  # Check if job was cancelled
```

### Processing Result
```python
class ProcessingResult:
    output_files: list[OutputFile]       # Files to upload as results
    metadata: dict                        # Optional metadata (page counts, etc.)
```

---

## 4. MVP Tool Handlers

### Merge PDF
- **Library:** pypdf
- **Input:** 2–20 PDF files
- **Config:** `{ "file_order": ["uuid1", "uuid2", ...] }`
- **Logic:** Append all pages in order using `PdfMerger`
- **Output:** Single merged PDF
- **Progress:** Per-file (file 1 of N merged...)

### Split PDF
- **Library:** pypdf
- **Input:** 1 PDF file
- **Config:** `{ "mode": "ranges"|"pages"|"every_n", "ranges": ["1-5", "6-10"] }`
- **Logic:** Extract pages based on ranges, create separate PDFs
- **Output:** Multiple PDF files (packaged as ZIP if > 1)
- **Progress:** Per-range

### Compress PDF
- **Library:** pikepdf
- **Input:** 1 PDF file
- **Config:** `{ "quality": "low"|"medium"|"high" }`
- **Logic:**
  - Low quality: aggressive image resampling + stream recompression
  - Medium quality: moderate resampling + linearization
  - High quality: lossless recompression + metadata stripping
- **Output:** Single compressed PDF
- **Progress:** Estimated based on input size

### Rotate PDF
- **Library:** pypdf
- **Input:** 1 PDF file
- **Config:** `{ "rotations": { "all": 90 } }` or `{ "rotations": { "pages": { "1": 90, "3": 180 } } }`
- **Logic:** Rotate specified pages by specified degrees
- **Output:** Single rotated PDF
- **Progress:** Per-page

---

## 5. Tool Registry

Tools are registered in a central registry that the API uses for validation, the frontend uses for rendering, and workers use for dispatch:

```python
# Conceptual registry structure

TOOL_REGISTRY = {
    "merge": {
        "handler": MergePDFHandler,
        "category": "organize",
        "tier": "free",
        "min_files": 2,
        "max_files": 20,
        "accepted_types": ["application/pdf"],
        "max_file_size": 50 * 1024 * 1024,  # 50 MB
        "timeout_seconds": 300,
        "retryable": True,
        "max_retries": 2,
    },
    "split": { ... },
    "compress": { ... },
    "rotate": { ... },
}
```

### Why a registry?
- Single source of truth for tool capabilities
- API validates requests against registry before creating jobs
- Frontend can dynamically render tool pages from registry data
- Workers use registry to dispatch to correct handler
- Easy to add new tools without touching existing code

---

## 6. File Validation

### Layer 1: Client-Side (Frontend)
- File extension check
- File size check
- MIME type from `File.type` (basic, can be spoofed)
- Provides fast feedback, not a security boundary

### Layer 2: API Server
- File size from `Content-Length` header
- MIME type validation
- File count per tool limits
- Rate limit enforcement

### Layer 3: Worker (Security Boundary)
- **Magic bytes** validation (read first 1024 bytes for file signature)
- **PDF structure** validation (is it a parseable PDF?)
- **Malicious content scan:**
  - Check for `/JS`, `/JavaScript`, `/OpenAction`, `/AA` (automatic actions)
  - Check for embedded files
  - Check for external URI references
  - Log warnings but do not block (some legitimate PDFs have these)
- **File size re-check** (in case metadata was spoofed)

```python
# Conceptual validation rules
SUSPICIOUS_PDF_KEYS = [
    "/JS",
    "/JavaScript",
    "/OpenAction",
    "/AA",
    "/Launch",
    "/SubmitForm",
    "/ImportData",
]
```

> **Decision:** For MVP, log suspicious elements but allow processing. In future, add configurable security levels and sandboxed rendering.

---

## 7. Temporary File Management

### Directory Structure
```
/tmp/docforge/
├── jobs/
│   ├── {job_id_1}/
│   │   ├── input/
│   │   │   ├── file1.pdf
│   │   │   └── file2.pdf
│   │   └── output/
│   │       └── merged.pdf
│   └── {job_id_2}/
│       └── ...
```

### Cleanup Strategy
1. **Worker cleanup:** After successful processing or failure, delete the job's temp directory
2. **Celery Beat sweep:** Every 15 minutes, scan `/tmp/docforge/jobs/` for directories older than 30 minutes and delete them (catches orphaned temp files from crashed workers)
3. **Container restart:** Temp directories are on ephemeral storage; container restart clears them automatically
4. **Object Storage cleanup:** Separate Celery Beat task deletes files from object storage based on `expires_at` timestamps

---

## 8. Progress Reporting

Workers report progress through Redis pub/sub, which the API server streams to clients via SSE:

```
Worker → Redis PUBLISH job:{job_id}:progress → API SSE endpoint → Browser EventSource
```

### Progress Events
```json
{"type": "status", "status": "PROCESSING", "progress": 0}
{"type": "progress", "progress": 25, "message": "Merging file 1 of 4..."}
{"type": "progress", "progress": 50, "message": "Merging file 2 of 4..."}
{"type": "progress", "progress": 75, "message": "Merging file 3 of 4..."}
{"type": "progress", "progress": 100}
{"type": "completed", "output_files": [...]}
```

### Fallback
If SSE connection drops, the frontend falls back to polling `GET /api/v1/jobs/{job_id}` every 3 seconds.

---

## 9. Error Handling & Retries

### Error Categories

| Category | Retryable | Example |
|----------|-----------|---------|
| **Validation Error** | No | Invalid PDF, wrong file type |
| **Processing Error** | Maybe | Out of memory, unexpected PDF structure |
| **Storage Error** | Yes | S3 timeout, network issue |
| **Timeout** | Yes | Processing took too long (retry with more resources) |
| **System Error** | Yes | Worker crashed |

### Retry Strategy
- Max retries: 2 (configurable per tool)
- Retry delay: Exponential backoff (30s, 120s)
- Only `Storage Error`, `Timeout`, and `System Error` are retried
- Each retry re-downloads files and starts from scratch (idempotent)
- After max retries, job is set to FAILED with a user-friendly error message

### Timeout Configuration
- **Soft timeout:** Sends SIGUSR1, allows graceful cleanup (e.g., 240s)
- **Hard timeout:** Sends SIGKILL, Celery marks task as failed (e.g., 300s)

---

## 10. Object Storage Key Structure

```
{bucket}/
├── inputs/
│   └── {YYYY}/{MM}/{DD}/
│       └── {job_id}/
│           ├── {file_id_1}.pdf
│           └── {file_id_2}.pdf
├── outputs/
│   └── {YYYY}/{MM}/{DD}/
│       └── {job_id}/
│           └── {file_id_3}.pdf
└── thumbnails/  (future)
    └── {YYYY}/{MM}/{DD}/
        └── {job_id}/
            └── {file_id_1}_thumb.png
```

### Why date-partitioned paths?
- Easier lifecycle management (delete old date prefixes)
- Better S3 performance at scale (avoids hot key prefixes)
- Simplified debugging (quickly find files from a specific day)

---

## 11. Adding a New Tool (Checklist)

When adding a new PDF tool to the system, follow this checklist:

1. **Define tool handler** implementing `ToolHandler` interface
2. **Define config schema** (JSON Schema for tool-specific parameters)
3. **Register in `TOOL_REGISTRY`** with limits and capabilities
4. **Add Celery task** that uses base pipeline with new handler
5. **Add frontend tool page** using shared Tool Page template
6. **Add API validation** (typically automatic via registry)
7. **Write tests:**
   - Unit tests for handler logic
   - Integration test for full pipeline (upload → process → download)
   - Edge case tests (empty PDF, huge PDF, corrupted PDF)
8. **Add to SEO sitemap** and create tool landing page content
9. **Update documentation**
