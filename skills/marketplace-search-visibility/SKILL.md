---
name: marketplace-search-visibility
description: Search a marketplace for keywords, check whether Websoft9 products appear in the results, record where they appear, and produce a short visibility report. Preliminary framework; not fully implemented.
---

# Marketplace Search Visibility

## Goal and scope

For a given marketplace and search keyword, determine whether products from Websoft9 appear in the search results, where they appear (rank, section, recommendation slot), and summarize the result in a report. This skill is an initial framework and does not yet implement every marketplace.

## Data sources

- Marketplace search page or search API for the target cloud platform.
- Public Websoft9 product names and supplier name for matching.
- Use a browser session or API client that preserves the marketplace's normal search behavior.

## Procedure

1. **Define the search.** Record the marketplace, keyword, locale, filters, and date.
2. **Run the search.** Execute the search and capture the first result page.
3. **Match products.** Identify results whose product name or supplier belongs to Websoft9.
4. **Record position.** Note the result rank, page, and any special placement such as a featured or ad slot.
5. **Write the report.** Summarize matches and non-matches.

## Stopping conditions

- Stop when the first result page is captured and Websoft9 matches are recorded, unless a multi-page check is explicitly requested.
- Stop and report the blocker if the marketplace requires authentication, captcha, or another unavailable dependency.
- Do not guess rankings or placements that were not observed.

## Expected output

A short markdown report containing:

- Marketplace, keyword, locale, filters, and check date
- Whether Websoft9 products appeared
- Each matching product, its rank/page, and placement
- Limitations and unverified items
