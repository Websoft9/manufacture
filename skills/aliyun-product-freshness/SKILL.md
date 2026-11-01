---
name: aliyun-product-freshness
description: Query published and visible Aliyun image products for a supplier, match product names to Websoft9 docker-library apps, compare versions, and create one issue for confirmed outdated products.
---

# Aliyun Marketplace Image Version Check

## Goal and scope

Check all **published and visible image products** in the Aliyun Marketplace from supplier **长沙网久软件有限公司**. Identify products whose application version is older than the current version in `Websoft9/docker-library`, then create one concise issue in this repository summarizing the findings. Do not create an issue if no outdated products are confirmed.

## Data sources and credentials

- Product catalog: Aliyun `Market` API version `2015-11-01`, [`DescribeProducts`](https://next.api.aliyun.com/document/Market/2015-11-01/DescribeProducts).
- Application catalog and versions: [`Websoft9/docker-library`](https://github.com/Websoft9/docker-library). Prefer machine-readable metadata, version manifests, and maintenance documentation in the matching app directory. Check the upstream project's official release information when needed to confirm its latest stable version.
- Read Aliyun credentials from a secure environment through the Aliyun SDK/OpenAPI client, for example `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`. Also set `ALIBABA_CLOUD_SECURITY_TOKEN` when using temporary STS credentials. Use the workflow's `GITHUB_TOKEN` or `gh` authentication for GitHub operations.
- Never print or store credentials, signed requests, or full sensitive API responses. Keep only the product fields and public links needed to support the findings.

## Procedure

1. **Verify the API contract.** Read the Aliyun API documentation and confirm the current request parameters, pagination method, response path, product-status field, and visibility field/enumeration. Follow the documented pagination method to enumerate all results. If supported, filter by the exact `SupplierName` value `长沙网久软件有限公司` and narrow by product type/status. Still verify the exact supplier name in each result, that it is an image product, and that it is published and publicly visible.
2. **Verify completeness.** Fetch every page until the API indicates there are no more results. Record the page count and the number of products remaining after filtering. Do not treat a page limit as a complete result. If the API response does not distinguish published and visible products, stop and report the missing fields; do not assume hidden products are visible.
3. **Match applications.** For each qualifying product, use its `ProductItem.name` (following the actual response structure) to match an app under `docker-library/apps/`. Ignore clear title modifiers such as cloud provider, operating system, deployment method, and plan. Use repository metadata or documentation to support aliases. Mark ambiguous products as unmatched and exclude them from version comparisons.
4. **Extract and compare versions.** Extract the product's application version from `ProductItem.ShortDescription`. Read the current version from the matching `docker-library` app metadata, checking the upstream stable release when needed. Compare semantic versions for the same application, not lexicographic strings; ignore a leading `v` when appropriate. A prerelease must not be treated as newer than its corresponding stable release. If either version is missing, ambiguous, or from an incompatible version scheme, mark the product unverified rather than outdated.
5. **Summarize differences.** Include only confirmed outdated products in the issue. Group entries by application and consolidate OS/plan variants where useful, but preserve every product title and product code/details link when available. Include the application, marketplace version, `docker-library` version, and source links for each finding.
6. **Check for duplicates and create an issue.** Search open issues in `Websoft9/manufacture` by title and content to avoid duplicating the same check. If outdated products are confirmed and no equivalent open issue exists, create one English issue with a concise title such as `[Aliyun] Outdated Marketplace Images: <number of apps> apps`. The body should state the supplier, check date, number of qualifying products, and a grouped version-difference table. Briefly note unmatched and unverified counts if any. Use the GitHub MCP server or `gh issue create`; do not modify marketplace task JSON files.
7. **Report the outcome.** Return the issue URL if one was created, the number of outdated apps/products, the number of qualifying products checked, and unmatched/unverified counts. If nothing is outdated, say that no issue was created. If the check is incomplete or the API is unavailable, state the blocker.

## Issue table format

```text
| Application | Aliyun product (product code) | Product version | docker-library version |
| ... | ... | ... | ... |
```

Never include unverified versions, invisible products, or products matched only by vague keywords in the confirmed-outdated list.
