# SEO Architecture

## 1. Overview

DocForge's primary user acquisition channel is organic search. Users search for specific PDF tasks (e.g., "merge pdf online", "compress pdf free") and expect to land on a page that immediately solves their problem. The **tool IS the content**.

---

## 2. SEO Strategy

### Core Principles
1. **Utility-first pages** — Each tool page is a functional landing page, not a content page
2. **One page per tool** — Every tool gets a dedicated, indexable URL
3. **Programmatic SEO** — Tool pages are generated from a data model, ensuring consistency
4. **Minimal but strategic copy** — Enough text for search engines to understand purpose, not walls of text
5. **Internal linking mesh** — Every tool page links to related tools

### Target Keyword Structure
```
Primary:    [action] + pdf + [modifier]
Examples:   "merge pdf online"
            "compress pdf free"
            "split pdf by pages"
            "rotate pdf online free"
            "pdf to word converter"
```

---

## 3. URL Structure

```
https://docforge.com/                        — Homepage
https://docforge.com/merge-pdf               — Merge tool
https://docforge.com/split-pdf               — Split tool
https://docforge.com/compress-pdf            — Compress tool
https://docforge.com/rotate-pdf              — Rotate tool
https://docforge.com/extract-pages           — Extract pages
https://docforge.com/pdf-to-jpg              — PDF to JPG
https://docforge.com/jpg-to-pdf              — JPG to PDF
https://docforge.com/tools                   — All tools directory
https://docforge.com/blog/{slug}             — Blog posts (Tier 2+)
https://docforge.com/pricing                 — Pricing page
https://docforge.com/about                   — About page
https://docforge.com/privacy                 — Privacy policy
https://docforge.com/terms                   — Terms of service
```

### URL Rules
- Lowercase, hyphenated slugs
- No trailing slashes (canonical without slash)
- No query parameters for tool pages (clean URLs)
- Consistent pattern: `/{tool-slug}`

---

## 4. Page Structure (Tool Pages)

Each tool page follows a consistent template optimized for both SEO and usability:

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                      │
│  Logo | Tool Nav (Merge · Split · Compress · Rotate · ...) │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  <h1>Merge PDF Files Online — Free</h1>                     │
│  <p>Combine multiple PDF documents into a single file.       │
│  Fast, secure, and free. No registration required.</p>       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  │              DRAG & DROP UPLOAD AREA                   │  │
│  │                                                       │  │
│  │          Drop PDF files here or click to browse        │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  [Uploaded files list / reorder UI / tool config]            │
│                                                              │
│  [ ████████  MERGE PDF  ████████ ]                          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  <h2>How to Merge PDF Files</h2>                            │
│  1. Upload your PDF files above                              │
│  2. Drag to reorder (optional)                               │
│  3. Click "Merge PDF"                                        │
│  4. Download your merged PDF                                 │
│                                                              │
│  <h2>Why Use DocForge to Merge PDFs?</h2>                   │
│  - Free, no registration                                     │
│  - Files deleted after 2 hours                               │
│  - Works on all devices                                      │
│  - No software installation needed                           │
│                                                              │
│  <h2>Frequently Asked Questions</h2>                        │
│  - Is it safe to merge PDFs online?                          │
│  - What's the maximum file size?                             │
│  - How many files can I merge at once?                       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  <h2>Related Tools</h2>                                     │
│  [Split PDF] [Compress PDF] [Rotate PDF] [Reorder Pages]   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                      │
│  All Tools · Privacy · Terms · About                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Technical SEO Implementation

### Next.js Rendering Strategy
- **Tool pages:** Static Site Generation (SSG) via `generateStaticParams()`
  - Why: Instant load, cacheable at CDN, great for SEO crawlers
  - Tool metadata comes from the tool registry (rebuild on tool changes)
- **User-specific pages:** Server-Side Rendering (SSR)
  - Job status, account pages — not indexed

### Meta Tags (per tool page)
```html
<head>
  <title>Merge PDF Files Online — Free | DocForge</title>
  <meta name="description" content="Merge multiple PDF files into one document online. Free, fast, and secure. No registration required. Files auto-deleted after 2 hours." />
  <link rel="canonical" href="https://docforge.com/merge-pdf" />

  <!-- Open Graph -->
  <meta property="og:title" content="Merge PDF Files Online — Free" />
  <meta property="og:description" content="Combine multiple PDF documents into one. Fast, free, secure." />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://docforge.com/merge-pdf" />
  <meta property="og:image" content="https://docforge.com/og/merge-pdf.png" />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Merge PDF Files Online — Free" />
</head>
```

### Structured Data (JSON-LD)
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "DocForge Merge PDF",
  "applicationCategory": "UtilitiesApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "ratingCount": "1200"
  }
}
```

And FAQ schema for each tool page:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is it safe to merge PDFs online?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. DocForge processes files securely and automatically deletes all uploaded files within 2 hours."
      }
    }
  ]
}
```

### Sitemap
- Auto-generated `sitemap.xml` at `/sitemap.xml`
- Updated when tools are added
- Includes all tool pages, homepage, and static pages
- Submitted to Google Search Console

### robots.txt
```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /dashboard/
Sitemap: https://docforge.com/sitemap.xml
```

---

## 6. Performance SEO

| Metric | Target | How |
|--------|--------|-----|
| **LCP** (Largest Contentful Paint) | < 2.5s | SSG, CDN caching, optimized images |
| **FID** (First Input Delay) | < 100ms | Minimal JS on initial load |
| **CLS** (Cumulative Layout Shift) | < 0.1 | Fixed-size placeholders, font display swap |
| **TTFB** (Time to First Byte) | < 200ms | Edge caching via Cloudflare/Vercel |

### Optimization Techniques
- SSG for tool pages (HTML pre-rendered at build time)
- Image optimization with Next.js `<Image>` component
- Code splitting per tool page (each tool only loads its own JS)
- Font preloading for primary typeface
- Critical CSS inlined
- Lazy-load below-fold content (FAQ section, related tools)

---

## 7. Internal Linking Strategy

```
Homepage
├── links to all tool category pages
├── links to top 6 most popular tools
│
Tool Page (e.g., Merge PDF)
├── Header nav → all tools
├── Related tools section → 4-6 related tools
├── FAQ links → other relevant tool pages
│
All Tools Page (/tools)
├── Grid of all tools organized by category
├── Each tool card links to its tool page
│
Blog (Tier 2+)
├── "How to merge PDF files" → links to Merge tool
├── "Best ways to compress PDF" → links to Compress tool
```

---

## 8. Content Strategy (Post-MVP)

| Content Type | Purpose | SEO Value |
|-------------|---------|-----------|
| Tool pages | Primary conversion pages | Direct intent keywords |
| Blog posts | Long-tail keywords, backlinks | Informational queries |
| Comparison pages | "DocForge vs iLovePDF" | Brand queries |
| How-to guides | Tutorial content | Informational + links |
| Changelog | Freshness signal | Trust |

---

## 9. Analytics Setup

| Tool | Purpose |
|------|---------|
| **Google Search Console** | Index coverage, search performance |
| **Google Analytics 4** (or Plausible) | Traffic, user behavior |
| **Core Web Vitals monitoring** | Performance tracking |

> **Privacy note:** Consider using **Plausible** or **Umami** (self-hosted) instead of GA4 to avoid cookie consent requirements and align with the privacy-first brand.
