import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  TOOL_SEO_REGISTRY,
  getAllToolSlugs,
  getToolSeoData,
  getToolMetadata,
  getSiteUrl,
  generateToolJsonLd,
} from "./tools-seo";
import sitemap from "@/app/sitemap";
import robots from "@/app/robots";

describe("Part 18 — SEO Architecture & Tool Landing Page Metadata", () => {
  const originalEnv = process.env.NEXT_PUBLIC_SITE_URL;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_SITE_URL;
  });

  afterEach(() => {
    if (originalEnv) {
      process.env.NEXT_PUBLIC_SITE_URL = originalEnv;
    } else {
      delete process.env.NEXT_PUBLIC_SITE_URL;
    }
  });

  it("covers all 13 PDF tools in the registry", () => {
    const slugs = getAllToolSlugs();
    expect(slugs).toHaveLength(13);

    const expectedTools = [
      "merge",
      "split",
      "compress",
      "rotate",
      "watermark",
      "page-numbers",
      "protect",
      "unlock",
      "extract-pages",
      "organize-pdf",
      "pdf-to-jpg",
      "jpg-to-pdf",
      "repair-pdf",
    ];

    for (const tool of expectedTools) {
      expect(slugs).toContain(tool);
      expect(getToolSeoData(tool)).toBeDefined();
    }
  });

  it("ensures each tool has unique metadata (title, description, h1, path)", () => {
    const slugs = getAllToolSlugs();
    const titles = new Set<string>();
    const descriptions = new Set<string>();
    const h1s = new Set<string>();
    const paths = new Set<string>();

    for (const slug of slugs) {
      const data = getToolSeoData(slug)!;

      expect(titles.has(data.title)).toBe(false);
      titles.add(data.title);

      expect(descriptions.has(data.metaDescription)).toBe(false);
      descriptions.add(data.metaDescription);

      expect(h1s.has(data.h1)).toBe(false);
      h1s.add(data.h1);

      expect(paths.has(data.path)).toBe(false);
      paths.add(data.path);

      // Verify content length & search friendliness
      expect(data.title.length).toBeGreaterThan(20);
      expect(data.title.length).toBeLessThan(80);
      expect(data.metaDescription.length).toBeGreaterThan(60);
      expect(data.metaDescription.length).toBeLessThan(180);
      expect(data.keywords.length).toBeGreaterThanOrEqual(4);
      expect(data.h1.length).toBeGreaterThan(5);
      expect(data.subtitle.length).toBeGreaterThan(50);
    }

    expect(titles.size).toBe(13);
    expect(descriptions.size).toBe(13);
    expect(h1s.size).toBe(13);
    expect(paths.size).toBe(13);
  });

  it("configures site URL safely without localhost in canonical metadata", () => {
    expect(getSiteUrl()).toBe("https://docforge.com");

    process.env.NEXT_PUBLIC_SITE_URL = "https://pdf.example.org";
    expect(getSiteUrl()).toBe("https://pdf.example.org");

    // Clean trailing slash
    process.env.NEXT_PUBLIC_SITE_URL = "https://pdf.example.org/";
    expect(getSiteUrl()).toBe("https://pdf.example.org");
  });

  it("generates correct Next.js Metadata with canonical URL and OpenGraph", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "https://docforge.app";
    const meta = getToolMetadata("merge");

    expect(meta.title).toContain("Merge PDF Files Online");
    expect(meta.alternates?.canonical).toBe("https://docforge.app/merge");
    expect(meta.openGraph?.title).toContain("Merge PDF Files Online");
    expect(meta.openGraph?.url).toBe("https://docforge.app/merge");
    expect(meta.twitter?.title).toContain("Merge PDF Files Online");
  });

  it("generates valid, crawlable sitemap containing only public canonical routes", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "https://docforge.com";
    const entries = sitemap();

    // 1 home + 1 tools directory + 2 legal pages + 13 tools = 17 routes
    expect(entries).toHaveLength(17);

    const urls = entries.map((e) => e.url);
    expect(urls).toContain("https://docforge.com/");
    expect(urls).toContain("https://docforge.com/tools");
    expect(urls).toContain("https://docforge.com/privacy");
    expect(urls).toContain("https://docforge.com/terms");
    expect(urls).toContain("https://docforge.com/merge");
    expect(urls).toContain("https://docforge.com/split");
    expect(urls).toContain("https://docforge.com/compress");
    expect(urls).toContain("https://docforge.com/rotate");
    expect(urls).toContain("https://docforge.com/watermark");
    expect(urls).toContain("https://docforge.com/page-numbers");
    expect(urls).toContain("https://docforge.com/protect");
    expect(urls).toContain("https://docforge.com/unlock");
    expect(urls).toContain("https://docforge.com/extract-pages");
    expect(urls).toContain("https://docforge.com/organize-pdf");
    expect(urls).toContain("https://docforge.com/pdf-to-jpg");
    expect(urls).toContain("https://docforge.com/jpg-to-pdf");
    expect(urls).toContain("https://docforge.com/repair-pdf");

    // Must not contain internal api or job routes
    for (const url of urls) {
      expect(url).not.toContain("/api/");
      expect(url).not.toContain("/jobs/");
    }
  });

  it("generates robots.txt disallowing internal endpoints and specifying sitemap", () => {
    process.env.NEXT_PUBLIC_SITE_URL = "https://docforge.com";
    const config = robots();

    expect(config.rules).toBeDefined();
    const rules = Array.isArray(config.rules) ? config.rules[0] : config.rules;
    expect(rules.userAgent).toBe("*");
    expect(rules.allow).toBe("/");
    expect(rules.disallow).toContain("/api/");
    expect(rules.disallow).toContain("/_next/");
    expect(config.sitemap).toBe("https://docforge.com/sitemap.xml");
  });

  it("generates valid JSON-LD with WebApplication, WebPage, HowTo, and FAQPage schemas without fake ratings", () => {
    const siteUrl = getSiteUrl();
    for (const slug of getAllToolSlugs()) {
      const tool = getToolSeoData(slug)!;
      const jsonLdObj = generateToolJsonLd(tool, siteUrl);

      // Must serialize to valid JSON string
      const jsonStr = JSON.stringify(jsonLdObj);
      const parsed = JSON.parse(jsonStr);

      expect(parsed["@context"]).toBe("https://schema.org");
      expect(Array.isArray(parsed["@graph"])).toBe(true);

      const graph = parsed["@graph"];
      const app = graph.find((item: any) => item["@type"] === "WebApplication");
      const webPage = graph.find((item: any) => item["@type"] === "WebPage");
      const howTo = graph.find((item: any) => item["@type"] === "HowTo");
      const faq = graph.find((item: any) => item["@type"] === "FAQPage");

      expect(app).toBeDefined();
      expect(app.name).toContain("DocForge");
      expect(["UtilitiesApplication", "SecurityApplication"]).toContain(app.applicationCategory);
      expect(app.offers.price).toBe("0");
      expect(app.operatingSystem).toBe("All");
      expect(app.browserRequirements).toBeDefined();
      // Crucial: No fake ratings or invented reviews
      expect((app as any).aggregateRating).toBeUndefined();
      expect((app as any).review).toBeUndefined();

      expect(webPage).toBeDefined();
      expect(webPage.name).toBe(tool.title);
      expect(webPage.url).toBe(`${siteUrl}${tool.path}`);
      expect(webPage.isPartOf["@type"]).toBe("WebSite");

      expect(howTo).toBeDefined();
      expect(howTo.name).toBe(tool.howToName);
      expect(howTo.step).toHaveLength(tool.steps.length);
      for (let i = 0; i < howTo.step.length; i++) {
        expect(howTo.step[i]["@type"]).toBe("HowToStep");
        expect(howTo.step[i].position).toBe(i + 1);
        expect(howTo.step[i].name).toBe(tool.steps[i].name);
        expect(howTo.step[i].text).toBe(tool.steps[i].text);
      }

      expect(faq).toBeDefined();
      expect(faq.mainEntity).toHaveLength(tool.faqs.length);
      for (let i = 0; i < faq.mainEntity.length; i++) {
        expect(faq.mainEntity[i]["@type"]).toBe("Question");
        expect(faq.mainEntity[i].name).toBe(tool.faqs[i].question);
        expect(faq.mainEntity[i].acceptedAnswer["@type"]).toBe("Answer");
        expect(faq.mainEntity[i].acceptedAnswer.text).toBe(tool.faqs[i].answer);
      }
    }
  });


  it("validates internal linking mesh: related tools are valid and reciprocal", () => {
    const allSlugs = getAllToolSlugs();
    const validPaths = allSlugs.map((s) => `/${s}`);

    for (const slug of allSlugs) {
      const tool = getToolSeoData(slug)!;

      // Must link to at least 3 related tools
      expect(tool.relatedTools.length).toBeGreaterThanOrEqual(3);

      for (const related of tool.relatedTools) {
        // Must point to a valid tool path
        expect(validPaths).toContain(related.href);
        // Must not self-link
        expect(related.href).not.toBe(tool.path);
        expect(related.name.length).toBeGreaterThan(0);
        expect(related.description.length).toBeGreaterThan(0);
      }
    }
  });

});
