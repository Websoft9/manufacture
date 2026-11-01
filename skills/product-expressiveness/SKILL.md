---
name: product-expressiveness
description: Check a marketplace product's expressiveness and compliance evidence, including demo images, videos, cases, qualifications, and version information. Preliminary placeholder; not fully implemented.
---

# Product Expressiveness Check

## Goal and scope

Check whether a marketplace product presents sufficient and compliant expression content: demo images, demo videos, customer cases, qualifications, version information, and related compliance requirements. This skill is a placeholder and does not yet implement the full check.

## Data sources

- Marketplace product detail page or API.
- Product image, video, case, qualification, and version fields.
- Marketplace expression and compliance rules.

## Procedure

1. **Identify the product.** Record the marketplace, product name, and product ID.
2. **Check expression content.** Look for demo images, videos, cases, qualifications, and version information.
3. **Check compliance.** Compare the content against marketplace expression and compliance rules.
4. **Record findings.** List missing, unclear, or non-compliant items with evidence.

## Stopping conditions

- Stop and report the blocker if the product page or API is unavailable.
- Do not mark an item as missing without checking the actual product page or API response.

## Expected output

A short markdown report containing:

- Marketplace, product name, product ID, and check date
- Presence and quality of demo images, videos, cases, qualifications, and version information
- Compliance findings
- Limitations and unverified items
