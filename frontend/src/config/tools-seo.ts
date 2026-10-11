import type { Metadata } from "next";

export interface HowToStep {
  name: string;
  text: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface RelatedTool {
  name: string;
  href: string;
  description: string;
  category: "Organize" | "Optimize" | "Convert" | "Security";
}

export interface ToolSeoData {
  slug: string;
  path: string;
  title: string;
  metaDescription: string;
  h1: string;
  subtitle: string;
  category: "Organize" | "Optimize" | "Convert" | "Security";
  keywords: string[];
  howToName: string;
  howToDescription: string;
  steps: HowToStep[];
  faqs: FaqItem[];
  relatedTools: RelatedTool[];
  applicationCategory: string;
}

export const DEFAULT_PRODUCTION_SITE_URL = "https://docforge.com";

/**
 * Returns the configured canonical site URL for metadata, sitemap, and robots.txt.
 * Priority:
 * 1. NEXT_PUBLIC_SITE_URL environment variable
 * 2. Vercel deployment URL (if available)
 * 3. Default production domain (https://docforge.com)
 */
export const getSiteUrl = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_SITE_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, "");
  }

  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL.replace(/\/+$/, "")}`;
  }

  if (process.env.NODE_ENV === "production" && typeof window === "undefined") {
    if (!(globalThis as any).__docforge_site_url_warned) {
      console.warn(
        `[DocForge SEO Notice] NEXT_PUBLIC_SITE_URL is not set. Defaulting to ${DEFAULT_PRODUCTION_SITE_URL}. Set NEXT_PUBLIC_SITE_URL in production environment variables for your canonical domain.`
      );
      (globalThis as any).__docforge_site_url_warned = true;
    }
  }

  return DEFAULT_PRODUCTION_SITE_URL;
};

export const TOOLS_SEO_DATA: Record<string, ToolSeoData> = {
  merge: {
    slug: "merge",
    path: "/merge",
    title: "Merge PDF Files Online — Free & Fast | DocForge",
    metaDescription:
      "Combine multiple PDF files into one organized document. Drag and drop to reorder pages and merge up to 20 files. 100% private processing with zero third-party sharing.",
    h1: "Merge PDF Files Online",
    subtitle:
      "Combine two or more PDF documents into a single, cohesive file in seconds. Arrange pages in your desired sequence with drag-and-drop simplicity while preserving document formatting, text fidelity, and vector graphics.",
    category: "Organize",
    keywords: ["merge pdf", "combine pdf files", "join pdf online", "merge pdf free", "pdf joiner"],
    howToName: "How to Merge PDF Files Online",
    howToDescription: "Combine multiple PDF documents into a single file with DocForge in four easy steps.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Select PDF files",
        text: "Click 'Choose PDF files' or drag and drop between 2 and 20 PDF documents into the upload area.",
      },
      {
        name: "Arrange file sequence",
        text: "Use the up and down arrow buttons or drag cards to place your files in the exact order you want them merged.",
      },
      {
        name: "Set output filename",
        text: "Optionally customize your output PDF document name before starting the process.",
      },
      {
        name: "Merge & download",
        text: "Click 'Merge Files' to process on DocForge's secure worker pipeline and download your unified PDF document immediately.",
      },
    ],
    faqs: [
      {
        question: "How many PDF files can I merge at once in DocForge?",
        answer:
          "DocForge allows merging between 2 and 20 PDF files per batch, with each individual file up to 50 MB in size.",
      },
      {
        question: "Will merging degrade the visual quality or formatting of my PDFs?",
        answer:
          "No. DocForge utilizes lossless PDF stream combination, preserving all original fonts, vector artwork, images, and page dimensions without recompression.",
      },
      {
        question: "Are my uploaded documents stored on external servers or used for model training?",
        answer:
          "No. All PDF transformations run on DocForge's dedicated private worker pipeline. Files are never sent to third-party cloud APIs, and all uploaded files are automatically purged within 2 hours.",
      },
      {
        question: "Can I reorder files before merging them?",
        answer:
          "Yes. The interactive file list displays all selected documents with up and down buttons and drag handles so you can set the exact page sequence.",
      },

    ],
    relatedTools: [
      {
        name: "Split PDF",
        href: "/split",
        description: "Separate merged documents back into individual chapters or page ranges.",
        category: "Organize",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Reduce the size of your newly merged PDF for easy email sharing.",
        category: "Optimize",
      },
      {
        name: "Organize PDF",
        href: "/organize-pdf",
        description: "Visually rearrange, rotate, or delete individual pages in your PDF.",
        category: "Organize",
      },
    ],
  },

  split: {
    slug: "split",
    path: "/split",
    title: "Split PDF Files Online — Extract Pages & Ranges | DocForge",
    metaDescription:
      "Split PDF documents into separate files by page ranges or extract every page into individual PDFs packaged in a ZIP. Free, private, and fast.",
    h1: "Split PDF Files Online",
    subtitle:
      "Divide large PDF files into distinct documents with precision. Extract specific chapter page ranges (such as 1-5, 8-10) into separate PDFs or separate every single page into individual files packaged in a convenient ZIP archive.",
    category: "Organize",
    keywords: ["split pdf", "separate pdf pages", "divide pdf", "split pdf by page range", "extract pdf pages"],
    howToName: "How to Split a PDF File",
    howToDescription: "Divide a PDF document into separate files by page ranges or extract all pages.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload your PDF",
        text: "Select or drop your PDF document into the upload dropzone (up to 50 MB).",
      },
      {
        name: "Choose split mode",
        text: "Select 'Custom Ranges' to specify targeted page intervals or 'Extract All Pages' to split every page.",
      },
      {
        name: "Enter page intervals",
        text: "If using ranges, enter comma-separated page spans (e.g. '1-3, 5-8') with real-time validation.",
      },
      {
        name: "Process and download",
        text: "Click 'Split PDF' to download your resulting PDF files or packaged ZIP archive.",
      },
    ],
    faqs: [
      {
        question: "What are the two ways to split a PDF in DocForge?",
        answer:
          "You can either specify custom page ranges (like '1-4, 7-10') to create separate targeted PDFs, or extract every single page into its own individual PDF packaged in a ZIP archive.",
      },
      {
        question: "What happens if I enter an invalid page range?",
        answer:
          "DocForge validates your input in real time. If a range is malformed, inverted (e.g. 5-2), or exceeds total document length, clear validation feedback is shown before processing begins.",
      },
      {
        question: "Does splitting a PDF damage bookmarks or selectable text layers?",
        answer:
          "No. The underlying content streams, fonts, and text characters are preserved losslessly in each split slice.",
      },
      {
        question: "Is there a file size limit for splitting PDFs?",
        answer:
          "You can upload and split PDF files up to 50 MB in size.",
      },
    ],
    relatedTools: [
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine separate PDF slices into a single unified document.",
        category: "Organize",
      },
      {
        name: "Extract Pages",
        href: "/extract-pages",
        description: "Select specific pages from a document and merge them into one output PDF.",
        category: "Organize",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Shrink split files to reduce storage requirements.",
        category: "Optimize",
      },
    ],
  },

  compress: {
    slug: "compress",
    path: "/compress",
    title: "Compress PDF Online — Reduce PDF File Size | DocForge",
    metaDescription:
      "Reduce PDF file size without sacrificing readability. Choose from Recommended, Balanced, or Maximum compression tiers. 100% private and free.",
    h1: "Compress PDF Files Online",
    subtitle:
      "Optimize and shrink heavy PDF files for faster web sharing and email attachments. Choose between three compression presets to balance file size savings with visual clarity, protected by automatic negative savings prevention.",
    category: "Optimize",
    keywords: ["compress pdf", "reduce pdf size", "shrink pdf file", "compress pdf online free", "pdf optimizer"],
    howToName: "How to Compress a PDF Document",
    howToDescription: "Shrink your PDF file size while maintaining readability using DocForge.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload your document",
        text: "Drag and drop your heavy PDF into the compression area.",
      },
      {
        name: "Select compression tier",
        text: "Pick Recommended (great quality, standard compression), Balanced (medium compression), or Maximum (smallest file size).",
      },
      {
        name: "Review estimated savings",
        text: "Inspect the compression tier parameters and quality tradeoffs before processing.",
      },
      {
        name: "Compress & download",
        text: "Click 'Compress PDF' to download your lightweight document and view your exact bytes saved.",
      },
    ],
    faqs: [
      {
        question: "What is DocForge's negative savings prevention?",
        answer:
          "If your PDF is already compressed or contains high-entropy streams that would expand under recompression, DocForge preserves your original document and marks it as already optimal, ensuring you never receive a larger file.",
      },
      {
        question: "What compression algorithms does DocForge utilize?",
        answer:
          "DocForge applies stream Deflate compression, unreferenced object pruning, cross-reference compaction, and intelligent image downsampling.",
      },
      {
        question: "Which compression tier should I choose?",
        answer:
          "Choose Recommended for everyday documents and resumes where crisp text and images are required. Choose Maximum when strict email size caps (like 2 MB or 5 MB) must be met.",
      },
      {
        question: "Are my files private during compression?",
        answer:
          "Yes. Processing runs entirely on DocForge's private worker pipeline, with no documents transmitted to third-party cloud providers. Files are automatically deleted within 2 hours.",
      },

    ],
    relatedTools: [
      {
        name: "PDF to JPG",
        href: "/pdf-to-jpg",
        description: "Convert PDF pages into high-resolution JPG images.",
        category: "Convert",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine compressed files together into a single presentation.",
        category: "Organize",
      },
      {
        name: "Protect PDF",
        href: "/protect",
        description: "Add password protection to your newly compressed PDF.",
        category: "Security",
      },
    ],
  },

  rotate: {
    slug: "rotate",
    path: "/rotate",
    title: "Rotate PDF Online — Permanently Rotate PDF Pages | DocForge",
    metaDescription:
      "Rotate PDF pages 90, 180, or 270 degrees clockwise. Rotate all pages or specific page ranges losslessly without recompression. Free and private.",
    h1: "Rotate PDF Pages Online",
    subtitle:
      "Fix sideways or upside-down PDF scans in seconds. Rotate all pages or targeted page numbers by 90°, 180°, or 270° clockwise. Transformations are strictly lossless, modifying PDF page orientation flags without altering vector curves or image fidelity.",
    category: "Organize",
    keywords: ["rotate pdf", "turn pdf pages", "rotate pdf permanently", "rotate pdf online", "fix sideways pdf"],
    howToName: "How to Rotate PDF Pages",
    howToDescription: "Permanently change the orientation of all or selected pages in a PDF document.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload your PDF",
        text: "Select or drop your PDF document onto the upload box.",
      },
      {
        name: "Choose rotation angle",
        text: "Click 90°, 180°, or 270° clockwise to set the new orientation.",
      },
      {
        name: "Select page scope",
        text: "Apply the rotation to all pages in the document or enter a selective range (e.g. 1, 3-5).",
      },
      {
        name: "Rotate & download",
        text: "Click 'Rotate PDF' to generate and download your corrected document.",
      },
    ],
    faqs: [
      {
        question: "Is the rotation permanent or just a preview setting?",
        answer:
          "It is permanent. DocForge updates the internal /Rotate dictionary entry of the PDF pages so the new orientation is recognized by all PDF viewers, printers, and operating systems.",
      },
      {
        question: "Will rotating my PDF degrade text sharpness or scan quality?",
        answer:
          "No. Rotation is 100% lossless because it only modifies the page orientation matrix without re-encoding bitmap streams or altering vector curves.",
      },
      {
        question: "Can I rotate only specific pages?",
        answer:
          "Yes. Choose the 'Specific Page Range' scope and type the page numbers you want rotated (e.g. '1, 3, 5-7'). All other pages remain in their original orientation.",
      },
      {
        question: "Can I rotate encrypted or password-protected PDFs?",
        answer:
          "Encrypted PDFs must first be unlocked using DocForge's Unlock PDF tool before page orientation can be modified.",
      },
    ],
    relatedTools: [
      {
        name: "Organize PDF",
        href: "/organize-pdf",
        description: "Visually rotate individual pages while reordering thumbnails.",
        category: "Organize",
      },
      {
        name: "Split PDF",
        href: "/split",
        description: "Divide rotated pages into individual PDF chapters.",
        category: "Organize",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Reduce file size after fixing page orientation.",
        category: "Optimize",
      },
    ],
  },

  watermark: {
    slug: "watermark",
    path: "/watermark",
    title: "Watermark PDF Online — Add Text Watermark to PDF | DocForge",
    metaDescription:
      "Add custom text watermarks to your PDF documents. Customize text, angle, opacity, font size, and 9 cardinal positions. Fast, private, and secure.",
    h1: "Add Watermark to PDF Documents",
    subtitle:
      "Protect confidential documents and assert copyright by overlaying dynamic text watermarks onto PDF pages. Customize text content, rotation angle (-180° to +180°), transparency opacity, font size, color, and 9 cardinal layout positions.",
    category: "Security",
    keywords: ["watermark pdf", "add watermark to pdf", "stamp pdf", "confidential watermark", "pdf copyright stamp"],
    howToName: "How to Add a Watermark to a PDF",
    howToDescription: "Stamp a custom text watermark onto your PDF document in four steps.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload your PDF",
        text: "Drop your document into the watermark tool.",
      },
      {
        name: "Enter watermark text",
        text: "Type your watermark string (e.g. 'CONFIDENTIAL', 'DRAFT', or your organization name).",
      },
      {
        name: "Customize styling",
        text: "Select position (such as Center), adjust rotation angle, set opacity slider, and pick a text color.",
      },
      {
        name: "Apply and download",
        text: "Click 'Add Watermark' to stamp the document and download your protected file.",
      },
    ],
    faqs: [
      {
        question: "Can I adjust the transparency of the watermark so underlying text remains readable?",
        answer:
          "Yes. The opacity slider allows setting transparency between 5% (very subtle) and 100% (completely opaque), with 30% being the recommended default for document readability.",
      },
      {
        question: "Where on the page can I position the watermark?",
        answer:
          "You can place watermarks in any of 9 positions: Center, Top-Left, Top-Center, Top-Right, Middle-Left, Middle-Right, Bottom-Left, Bottom-Center, or Bottom-Right.",
      },
      {
        question: "Can I watermark only selected pages?",
        answer:
          "Yes. You can choose to stamp all pages or enter a selective range (e.g. '1-3, 5') to watermark specific pages only.",
      },
      {
        question: "Does watermarking remove existing metadata or signatures?",
        answer:
          "Watermarking overlays a vector text layer over the existing pages while keeping the underlying document structure intact.",
      },
    ],
    relatedTools: [
      {
        name: "Protect PDF",
        href: "/protect",
        description: "Add AES-256 encryption and a password to prevent unauthorized viewing.",
        category: "Security",
      },
      {
        name: "Page Numbers",
        href: "/page-numbers",
        description: "Stamp header and footer numbering onto your document.",
        category: "Organize",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Optimize your watermarked PDF for smaller file size.",
        category: "Optimize",
      },
    ],
  },

  "page-numbers": {
    slug: "page-numbers",
    path: "/page-numbers",
    title: "Add Page Numbers to PDF Online — Free Header & Footer Stamping | DocForge",
    metaDescription:
      "Add page numbers to PDF documents. Customize format (Page X of Y, X of Y, etc.), starting page number, position, margin, and font size. 100% private.",
    h1: "Add Page Numbers to PDF Files",
    subtitle:
      "Stamp professional pagination onto PDF documents with custom numbering formats, margins, and alignment. Choose from header or footer positions, adjust starting numbers, and customize font styling for legal filings, academic papers, and reports.",
    category: "Organize",
    keywords: ["add page numbers to pdf", "pdf page numbering", "number pdf pages", "pdf bates numbering", "paginate pdf"],
    howToName: "How to Add Page Numbers to a PDF",
    howToDescription: "Stamp page numbers into headers or footers across your PDF document.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload document",
        text: "Select or drop your PDF into the upload area.",
      },
      {
        name: "Choose numbering format",
        text: "Select from 'Page {n} of {total}', '{n} of {total}', '{n} / {total}', or just '{n}'.",
      },
      {
        name: "Select position & styling",
        text: "Choose position (Bottom Center, Bottom Right, Top Right, etc.), starting page number, margin, and font size.",
      },
      {
        name: "Stamp & download",
        text: "Click 'Add Page Numbers' to download your numbered PDF.",
      },
    ],
    faqs: [
      {
        question: "What page number formats are available in DocForge?",
        answer:
          "DocForge supports four standard formats: 'Page X of Y' (default), 'X of Y', 'X / Y', and single digit 'X'.",
      },
      {
        question: "Can I start numbering from page 2 to skip a cover page?",
        answer:
          "Yes. You can customize the starting page number and specify page ranges so cover pages and title pages remain unnumbered.",
      },
      {
        question: "What positions on the page can I place the numbers?",
        answer:
          "You can position page numbers in 6 standard locations: Bottom-Center, Bottom-Right, Bottom-Left, Top-Center, Top-Right, or Top-Left.",
      },
      {
        question: "Can I change the margin distance from the edge of the page?",
        answer:
          "Yes. You can adjust the margin in points (e.g. 18 pt to 72 pt) to ensure numbers do not overlap with existing content.",
      },
    ],
    relatedTools: [
      {
        name: "Watermark PDF",
        href: "/watermark",
        description: "Add text overlays and confidentiality stamps to your PDF.",
        category: "Security",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine chapters before adding consistent sequential page numbers.",
        category: "Organize",
      },
      {
        name: "Organize PDF",
        href: "/organize-pdf",
        description: "Arrange pages in order before applying page numbers.",
        category: "Organize",
      },
    ],
  },

  protect: {
    slug: "protect",
    path: "/protect",
    title: "Protect PDF Online — Encrypt PDF with Password | DocForge",
    metaDescription:
      "Encrypt PDF files with AES-256 standard security and password protection. Passwords are never stored on disk or database. 100% private and free.",
    h1: "Protect PDF Files with Password Encryption",
    subtitle:
      "Secure sensitive documents against unauthorized access with standard AES-256 bit encryption. Set an owner and user password to lock your PDF so only authorized recipients with the password can open and view it.",
    category: "Security",
    keywords: ["protect pdf", "encrypt pdf", "password protect pdf", "lock pdf", "pdf security aes 256"],
    howToName: "How to Encrypt a PDF with a Password",
    howToDescription: "Protect a PDF with strong AES-256 encryption in four simple steps.",
    applicationCategory: "SecurityApplication",
    steps: [
      {
        name: "Select PDF file",
        text: "Drop your document into the encryption box.",
      },
      {
        name: "Enter secure password",
        text: "Type your desired password and confirm it in the verification field.",
      },
      {
        name: "Check password strength",
        text: "Ensure your password is at least 6 characters long and memorable.",
      },
      {
        name: "Encrypt & download",
        text: "Click 'Protect PDF' to apply AES-256 encryption and download your secured file.",
      },
    ],
    faqs: [
      {
        question: "What encryption standard does DocForge use to protect PDFs?",
        answer:
          "DocForge applies standard AES-256 bit encryption, the industry gold standard for PDF security recognized by Adobe Acrobat and all modern PDF readers.",
      },
      {
        question: "Is my password saved or stored in DocForge's database?",
        answer:
          "No. Passwords are held temporarily in ephemeral Redis storage and purged the moment the worker encrypts the document. Passwords are never written to PostgreSQL or disk logs.",
      },
      {
        question: "What happens if I forget the password I set?",
        answer:
          "Because AES-256 encryption cannot be cracked without the key, DocForge cannot recover a forgotten password. Keep a secure backup of your password.",
      },
      {
        question: "Can a protected PDF be converted or edited without the password?",
        answer:
          "No. Standard PDF viewers will require entering the correct password before rendering any pages or allowing edits.",
      },
    ],
    relatedTools: [
      {
        name: "Unlock PDF",
        href: "/unlock",
        description: "Remove password protection from a PDF when you know the password.",
        category: "Security",
      },
      {
        name: "Watermark PDF",
        href: "/watermark",
        description: "Add copyright notices or confidentiality marks to sensitive documents.",
        category: "Security",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Optimize encrypted files for smaller storage size.",
        category: "Optimize",
      },
    ],
  },

  unlock: {
    slug: "unlock",
    path: "/unlock",
    title: "Unlock PDF Online — Remove Password from PDF | DocForge",
    metaDescription:
      "Remove password protection and encryption from PDF documents. Enter your valid password once to generate an unencrypted PDF. 100% private.",
    h1: "Unlock Password-Protected PDF Files",
    subtitle:
      "Remove password security from your encrypted PDF files when you have the authorized password. Generate an open, unencrypted PDF copy that opens directly without prompting for credentials every time.",
    category: "Security",
    keywords: ["unlock pdf", "remove pdf password", "decrypt pdf", "unprotect pdf", "open locked pdf"],
    howToName: "How to Remove Password from a PDF",
    howToDescription: "Decrypt a password-protected PDF to create an open, accessible document.",
    applicationCategory: "SecurityApplication",
    steps: [
      {
        name: "Upload locked PDF",
        text: "Drop your password-protected document into the upload dropzone.",
      },
      {
        name: "Enter document password",
        text: "Type the valid password used to secure the file.",
      },
      {
        name: "Validate credentials",
        text: "DocForge verifies the password against the PDF encryption structure.",
      },
      {
        name: "Download unlocked PDF",
        text: "Download your decrypted PDF, ready to open without password prompts.",
      },
    ],
    faqs: [
      {
        question: "Does DocForge brute-force or bypass passwords without knowing them?",
        answer:
          "No. DocForge does not crack or bypass passwords. You must provide the valid password to decrypt the document structure legitimately.",
      },
      {
        question: "Why would I want to unlock a PDF?",
        answer:
          "Unlocking is useful for removing repeated password prompts on personal tax returns, bank statements, or utility bills before archiving or sharing with trusted accountants.",
      },
      {
        question: "Is my entered password safe during the unlocking process?",
        answer:
          "Yes. Passwords are held ephemerally in volatile memory for the duration of the job and deleted immediately after decryption. They are never logged or stored.",
      },
      {
        question: "Can an unlocked PDF be re-encrypted later?",
        answer:
          "Yes. You can use DocForge's Protect PDF tool at any time to apply a new password or encryption key.",
      },
    ],
    relatedTools: [
      {
        name: "Protect PDF",
        href: "/protect",
        description: "Re-encrypt documents with a new password.",
        category: "Security",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine unlocked files with other PDF documents.",
        category: "Organize",
      },
      {
        name: "PDF to JPG",
        href: "/pdf-to-jpg",
        description: "Convert pages from unlocked PDFs into JPG images.",
        category: "Convert",
      },
    ],
  },

  "extract-pages": {
    slug: "extract-pages",
    path: "/extract-pages",
    title: "Extract Pages from PDF Online — Save Selected Pages | DocForge",
    metaDescription:
      "Extract specific pages or page ranges from a PDF and combine them into a clean new document. Enter custom ranges like 1, 3-5, 8. Free and private.",
    h1: "Extract Pages from PDF Documents",
    subtitle:
      "Selectively pull specific pages or sections out of a PDF document and save them as a fresh, standalone PDF. Extract individual pages, custom page ranges (e.g. 1, 3-5, 8), or entire chapters with zero quality degradation.",
    category: "Organize",
    keywords: ["extract pdf pages", "pull pages from pdf", "save selected pdf pages", "extract pages online", "export pdf pages"],
    howToName: "How to Extract Pages from a PDF",
    howToDescription: "Save selected pages from a PDF document into a new file.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload your PDF",
        text: "Select or drop your PDF document into the tool.",
      },
      {
        name: "Enter page selection",
        text: "Type custom page numbers or ranges (e.g. '1, 3-5, 9') or use quick range presets.",
      },
      {
        name: "Review extraction summary",
        text: "Confirm the total extracted page count matches your requirements.",
      },
      {
        name: "Extract & download",
        text: "Click 'Extract Pages' to generate and download your new PDF containing only the selected pages.",
      },
    ],
    faqs: [
      {
        question: "How does Extract Pages differ from Split PDF?",
        answer:
          "Extract Pages combines your selected pages into a single new output PDF document, whereas Split PDF divides pages into multiple separate files or a ZIP archive.",
      },
      {
        question: "What syntax can I use to select pages?",
        answer:
          "You can use single numbers ('1'), comma-separated lists ('1, 4, 7'), ranges ('3-8'), or mixed combinations ('1, 3-5, 9-12').",
      },
      {
        question: "Can I extract non-consecutive pages from different parts of the document?",
        answer:
          "Yes. You can pull pages from anywhere in the document (such as page 1, page 15, and page 30) into one cohesive output.",
      },
      {
        question: "Does page extraction preserve compressed object streams and fonts?",
        answer:
          "Yes. DocForge's extraction engine preserves all internal stream dictionaries, font descriptors, and image assets losslessly.",
      },
    ],
    relatedTools: [
      {
        name: "Split PDF",
        href: "/split",
        description: "Split a PDF into separate individual documents.",
        category: "Organize",
      },
      {
        name: "Organize PDF",
        href: "/organize-pdf",
        description: "Visually rearrange, delete, or duplicate pages with drag-and-drop.",
        category: "Organize",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine your extracted pages with other PDF files.",
        category: "Organize",
      },
    ],
  },

  "organize-pdf": {
    slug: "organize-pdf",
    path: "/organize-pdf",
    title: "Organize PDF Pages Online — Rearrange, Rotate & Delete | DocForge",
    metaDescription:
      "Visually organize PDF pages with real-time thumbnails. Drag and drop to reorder, rotate individual pages 90 degrees, duplicate, or delete. 100% private.",
    h1: "Organize and Reorder PDF Pages",
    subtitle:
      "Take complete visual control over your PDF page structure. Render real-time page thumbnails in your browser, drag and drop to reorder, rotate individual pages, duplicate key sections, and delete unwanted pages with full undo/redo history.",
    category: "Organize",
    keywords: ["organize pdf", "reorder pdf pages", "delete pdf pages", "rearrange pdf", "duplicate pdf pages"],
    howToName: "How to Organize PDF Pages Online",
    howToDescription: "Visually reorder, rotate, delete, and duplicate pages in a PDF document.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload PDF document",
        text: "Select your PDF file to load high-fidelity previews in the interactive grid.",
      },
      {
        name: "Rearrange pages",
        text: "Drag and drop page cards to reorder, or use keyboard arrow controls.",
      },
      {
        name: "Rotate or delete pages",
        text: "Click the rotate button on any thumbnail to turn it 90°, or click delete to remove it.",
      },
      {
        name: "Save & download",
        text: "Click 'Save & Organize' to compile your updated layout into a fresh PDF.",
      },
    ],
    faqs: [
      {
        question: "Are PDF thumbnails rendered on an external server or sent to the cloud?",
        answer:
          "No. Thumbnail previews are rendered client-side in your browser using DocForge's bundled, security-hardened PDF.js worker without server roundtrips. When you click Save & Organize, your updated page order is assembled on DocForge's private backend workers with automatic 2-hour deletion.",
      },

      {
        question: "Can I undo my changes if I accidentally delete a page?",
        answer:
          "Yes. The Organize PDF workspace maintains an in-memory undo and redo history stack so you can revert any reordering, deletion, or rotation step.",
      },
      {
        question: "Can I select and perform batch actions on multiple pages at once?",
        answer:
          "Yes. You can select multiple page cards to rotate or delete them simultaneously.",
      },
      {
        question: "Is there a limit to how many pages I can organize?",
        answer:
          "DocForge supports organizing documents up to 50 MB with responsive thumbnail pagination for smooth performance.",
      },
    ],
    relatedTools: [
      {
        name: "Rotate PDF",
        href: "/rotate",
        description: "Quickly rotate all pages in a document without thumbnail inspection.",
        category: "Organize",
      },
      {
        name: "Extract Pages",
        href: "/extract-pages",
        description: "Extract specific page numbers into a standalone file.",
        category: "Organize",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine multiple organized PDFs together.",
        category: "Organize",
      },
    ],
  },

  "pdf-to-jpg": {
    slug: "pdf-to-jpg",
    path: "/pdf-to-jpg",
    title: "Convert PDF to JPG Online — High Resolution Images | DocForge",
    metaDescription:
      "Convert PDF pages into high-quality JPG images. Choose standard 150 DPI or high-resolution 300 DPI with quality settings. Download as a ZIP archive. Free.",
    h1: "Convert PDF to JPG Images Online",
    subtitle:
      "Turn every page of your PDF document into crisp, high-resolution JPEG images. Select between standard 150 DPI for web sharing or print-quality 300 DPI for publishing, and download all converted images packaged in a tidy ZIP archive.",
    category: "Convert",
    keywords: ["pdf to jpg", "convert pdf to image", "pdf to jpeg", "extract images from pdf", "pdf to picture"],
    howToName: "How to Convert PDF Pages into JPG Images",
    howToDescription: "Convert every page of a PDF document into high-resolution JPG images.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload PDF",
        text: "Drag and drop your PDF into the converter.",
      },
      {
        name: "Select resolution",
        text: "Choose Standard (150 DPI, ideal for web and email) or High Resolution (300 DPI, ideal for printing and graphics).",
      },
      {
        name: "Set image quality",
        text: "Adjust the JPEG quality slider (default 85%).",
      },
      {
        name: "Convert & download ZIP",
        text: "Click 'Convert to JPG' to generate images and download the complete ZIP archive.",
      },
    ],
    faqs: [
      {
        question: "What is the difference between 150 DPI and 300 DPI conversion?",
        answer:
          "150 DPI is standard resolution that produces compact image files suitable for screen viewing, slides, and websites. 300 DPI renders double the pixel density, ensuring sharp print-ready output and fine text legibility.",
      },
      {
        question: "How are the converted images delivered?",
        answer:
          "All converted page images are numbered sequentially (e.g. page_1.jpg, page_2.jpg) and compressed into a single downloadable ZIP archive.",
      },
      {
        question: "What are the file size and page count limits for PDF to JPG?",
        answer:
          "DocForge supports PDFs up to 50 MB, converting up to 100 pages at 150 DPI or up to 50 pages at 300 DPI with an aggregate output safety limit of 250 MB.",
      },
      {
        question: "Are conversions processed using external third-party APIs?",
        answer:
          "No. Conversions are rendered directly on DocForge's own backend workers using native rendering libraries, keeping your documents confidential and never sent to external APIs.",
      },

    ],
    relatedTools: [
      {
        name: "JPG to PDF",
        href: "/jpg-to-pdf",
        description: "Convert JPG or JPEG images back into a formatted PDF document.",
        category: "Convert",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Reduce PDF file size before converting to images.",
        category: "Optimize",
      },
      {
        name: "Extract Pages",
        href: "/extract-pages",
        description: "Extract specific pages to convert only the sections you need.",
        category: "Organize",
      },
    ],
  },

  "jpg-to-pdf": {
    slug: "jpg-to-pdf",
    path: "/jpg-to-pdf",
    title: "Convert JPG to PDF Online — Combine Images to PDF | DocForge",
    metaDescription:
      "Convert JPG/JPEG images into a single PDF document. Drag and drop to reorder images, customize page size (A4, Letter, Fit), orientation, and margins. Free.",
    h1: "Convert JPG Images to PDF Documents",
    subtitle:
      "Transform multiple JPG and JPEG photos into a polished, professional PDF document. Reorder images visually with drag-and-drop, configure page orientation (Auto, Portrait, Landscape), select standard page dimensions (A4, Letter, or Fit to Image), and set clean margins.",
    category: "Convert",
    keywords: ["jpg to pdf", "convert images to pdf", "jpeg to pdf converter", "photos to pdf", "combine pictures to pdf"],
    howToName: "How to Convert JPG Images into a PDF",
    howToDescription: "Combine multiple JPG or JPEG images into a single structured PDF file.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload JPG images",
        text: "Select or drop up to 50 JPG or JPEG photos into the upload gallery.",
      },
      {
        name: "Arrange image order",
        text: "Drag thumbnails to set page order, or use the move earlier/later buttons.",
      },
      {
        name: "Configure page layout",
        text: "Choose orientation (Auto, Portrait, Landscape), page size (Fit to Image, A4, Letter), and margins (None, Small, Normal).",
      },
      {
        name: "Generate & download PDF",
        text: "Click 'Convert to PDF' to generate and download your combined PDF album or report.",
      },
    ],
    faqs: [
      {
        question: "How many images can I convert into a single PDF?",
        answer:
          "You can upload and combine up to 50 JPG/JPEG images in a single conversion job, with each image up to 25 MB in size.",
      },
      {
        question: "Does DocForge normalize EXIF camera orientation?",
        answer:
          "Yes. DocForge automatically reads EXIF orientation tags and rotates images upright so photos taken on smartphones or cameras display correctly.",
      },
      {
        question: "What page sizes and margin options are supported?",
        answer:
          "DocForge supports 'Fit to Image' (pages match photo dimensions exactly), standard 'A4' (210 x 297 mm), and 'US Letter' (8.5 x 11 in), with margin options of None (0 pt), Small (18 pt), or Normal (36 pt).",
      },
      {
        question: "Can I convert other image formats like PNG or WEBP?",
        answer:
          "This tool is specifically optimized for JPG and JPEG images. For best results, use standard .jpg or .jpeg files.",
      },
    ],
    relatedTools: [
      {
        name: "PDF to JPG",
        href: "/pdf-to-jpg",
        description: "Convert PDF documents into high-resolution JPG images.",
        category: "Convert",
      },
      {
        name: "Merge PDF",
        href: "/merge",
        description: "Combine your generated PDF with other existing PDF documents.",
        category: "Organize",
      },
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Reduce the size of your final photo PDF.",
        category: "Optimize",
      },
    ],
  },
  "repair-pdf": {
    slug: "repair-pdf",
    path: "/repair-pdf",
    title: "Repair PDF Files Online — Recover Corrupted PDFs Free | DocForge",
    metaDescription:
      "Repair corrupted or damaged PDF files online for free. Recover cross-reference tables, restore broken trailers, and salvage unreadable PDF pages safely with zero third-party APIs.",
    h1: "Repair Corrupted PDF Files",
    subtitle:
      "Analyze and restore structurally damaged, broken, or unreadable PDF documents. Reconstruct cross-reference tables, fix stream errors, and salvage intact pages safely on DocForge's dedicated private worker pipeline.",
    category: "Optimize",
    keywords: [
      "repair pdf",
      "fix corrupted pdf",
      "recover damaged pdf",
      "restore broken pdf",
      "repair pdf online",
      "pdf recovery free",
    ],
    howToName: "How to Repair Corrupted PDF Files Online",
    howToDescription: "Recover and salvage damaged PDF documents with DocForge in four simple steps.",
    applicationCategory: "UtilitiesApplication",
    steps: [
      {
        name: "Upload damaged PDF",
        text: "Click 'Choose PDF File' or drag and drop your corrupted or unreadable PDF into the upload area.",
      },
      {
        name: "Analyze document structure",
        text: "DocForge analyzes cross-reference tables, object streams, and trailer information to identify recoverable data.",
      },
      {
        name: "Reconstruct and salvage",
        text: "Click 'Repair PDF' to reconstruct damaged tables and salvage pages into a fresh, standard-compliant PDF.",
      },
      {
        name: "Download recovered PDF",
        text: "Download your newly repaired document immediately. All files are automatically purged from private storage within 2 hours.",
      },
    ],
    faqs: [
      {
        question: "What kinds of PDF damage can DocForge repair?",
        answer:
          "DocForge repairs damaged or truncated cross-reference (xref) tables, missing or corrupted trailer dictionaries, invalid startxref offsets, broken stream lengths, and missing EOF markers. If the underlying page streams are intact, DocForge rebuilds a clean, valid PDF.",
      },
      {
        question: "Can severely corrupted or overwritten files always be recovered?",
        answer:
          "If the actual page content or stream data has been overwritten with random bytes, truncated to zero bytes, or destroyed, recovery is not possible. DocForge clearly reports unrecoverable files rather than producing false promises.",
      },
      {
        question: "Will repairing a PDF overwrite my original upload?",
        answer:
          "No. DocForge never modifies or overwrites your uploaded original. Reconstructed pages and repaired xref structures are compiled into a newly generated document.",
      },
      {
        question: "Can DocForge repair password-protected or encrypted PDFs?",
        answer:
          "Password-protected PDFs must first be unlocked with the correct password before repair. If an encrypted PDF has corrupted encryption dictionaries, it cannot be decrypted.",
      },
      {
        question: "Are my uploaded damaged documents kept private?",
        answer:
          "Yes. File processing executes exclusively on DocForge's private worker infrastructure with zero third-party APIs. All temporary files are permanently purged within 2 hours.",
      },
    ],
    relatedTools: [
      {
        name: "Compress PDF",
        href: "/compress",
        description: "Optimize and compact the internal structure of your recovered PDF.",
        category: "Optimize",
      },
      {
        name: "Unlock PDF",
        href: "/unlock",
        description: "Remove passwords from protected PDFs before repairing.",
        category: "Security",
      },
      {
        name: "Split PDF",
        href: "/split",
        description: "Separate specific recovered pages or chapters into individual files.",
        category: "Organize",
      },
    ],
  },
};

export const TOOL_SEO_REGISTRY = TOOLS_SEO_DATA;

export const getAllToolSlugs = (): string[] => Object.keys(TOOLS_SEO_DATA);


export const getToolSeoData = (slug: string): ToolSeoData | undefined => {
  return TOOLS_SEO_DATA[slug];
};

export const getToolMetadata = (slug: string): Metadata => {
  const tool = getToolSeoData(slug);
  const siteUrl = getSiteUrl();

  if (!tool) {
    return {
      title: "DocForge - Free & Private PDF Tools",
      description: "Fast, private, and local PDF processing.",
    };
  }

  const canonicalUrl = `${siteUrl}${tool.path}`;

  return {
    title: tool.title,
    description: tool.metaDescription,
    keywords: tool.keywords,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: tool.title,
      description: tool.metaDescription,
      url: canonicalUrl,
      siteName: "DocForge",
      locale: "en_US",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: tool.title,
      description: tool.metaDescription,
    },
  };
};

/**
 * Generates JSON-LD structured data matching current Google Search Central requirements:
 * - Uses WebApplication (sub-type of SoftwareApplication) with genuine product attributes and zero fake reviews/ratings.
 * - Adds WebPage linked to the root WebSite for unambiguous page-level search context.
 * - Retains HowTo and FAQPage schemas strictly matching the visible DOM content.
 *   Note: While HowTo and FAQPage schemas are syntactically valid and match on-page text,
 *   Google Search Central does not guarantee rich result presentation for general utility sites.
 *   These schemas are provided solely for semantic precision and crawlability.
 */
export const generateToolJsonLd = (tool: ToolSeoData, siteUrl: string) => {
  const canonicalUrl = `${siteUrl}${tool.path}`;

  const webApp = {
    "@type": "WebApplication",
    "@id": `${canonicalUrl}#app`,
    name: `DocForge ${tool.h1}`,
    url: canonicalUrl,
    description: tool.metaDescription,
    applicationCategory: tool.applicationCategory,
    operatingSystem: "All",
    browserRequirements: "Requires modern web browser with HTML5 and JavaScript support",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
  };

  const webPage = {
    "@type": "WebPage",
    "@id": `${canonicalUrl}#webpage`,
    url: canonicalUrl,
    name: tool.title,
    description: tool.metaDescription,
    isPartOf: {
      "@type": "WebSite",
      "@id": `${siteUrl}#website`,
      name: "DocForge",
      url: siteUrl,
    },
  };

  const howTo = {
    "@type": "HowTo",
    name: tool.howToName,
    description: tool.howToDescription,
    step: tool.steps.map((step, idx) => ({
      "@type": "HowToStep",
      position: idx + 1,
      name: step.name,
      text: step.text,
    })),
  };

  const faqPage = {
    "@type": "FAQPage",
    mainEntity: tool.faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return {
    "@context": "https://schema.org",
    "@graph": [webApp, webPage, howTo, faqPage],
  };
};

