---
name: app-metadata
description: Generate and maintain per-application use cases and keywords for the marketplace site from the Websoft9 product catalog. Use when adding or refreshing application metadata before rebuilding the site.
---

# Application Metadata

## Goal and scope

Maintain `data/app-metadata.json`, one entry per application in
`product_en.json`, with English `useCases` and `keywords` used by the static
site's application detail pages. The same item shape can later be mapped to
Contentful fields.

## Data sources

- Product catalog: <https://artifact.websoft9.com/appstore/release/catalog/product_en.json>
- Existing metadata: `data/app-metadata.json`
- Optional marketplace links: <https://artifact.websoft9.com/cloud_data/offer.json>

## Procedure

1. Fetch the current product catalog and read the existing metadata file.
2. For each catalog `key`, generate or update:
   - `useCases`: one or two concise English sentences describing realistic
     buyer scenarios. Base this on `summary`, `overview`, `description`,
     categories, and related applications.
   - `keywords`: 1–15 English search phrases, each at most 50 characters.
     Prefer product names, categories, modules, and common buyer intents.
     Avoid internal implementation terms such as `docker`, `panel`, or
     `console`, and do not repeat generic words that add no search value.
3. Keep keys stable. Do not delete entries for applications that are
   temporarily absent from the catalog; they may return later.
4. Validate before writing:
   - every catalog key has an entry;
   - no duplicate keys;
   - `useCases` is non-empty;
   - `keywords` has 1–15 items, every item is at most 50 characters, and no
     item is duplicated within the same application.
5. Write UTF-8 JSON with `schemaVersion`, `generatedAt`, `source`, and `items`.
6. From `site/`, run `npm run check` and `npm run build`. The build fails when
   a catalog application has no metadata entry.

## Stopping conditions

- Stop and report if the catalog is unavailable or malformed.
- Do not invent capabilities, versions, support terms, or certifications that
  are not supported by the catalog or verified product pages.
- If an application has no `description`, base the copy on `overview` and
  `summary` and mention the limitation in the change summary.

## Expected output

- Updated `data/app-metadata.json`.
- A short report containing:
  - catalog and metadata counts;
  - added, updated, and retained entries;
  - validation results;
  - applications with limited source content or unverified claims.
- Future: map the same `items` fields to Contentful when its content model is
  available.
