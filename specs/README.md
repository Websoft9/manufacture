# Project Specifications (AI Quick Start)

- This repository manages Websoft9 marketplace product production and maintenance tasks. Existing platform data and issue workflows are core business assets.
- The business positioning and scope are defined in [`business-positioning.md`](business-positioning.md).
- GitHub Actions connects to AWS through OIDC; see [`cloud-connector.md`](cloud-connector.md).
- For product master data, personalized AWS AMI listing content and Catalog metadata update commands, see [`marketplace-product-content.md`](marketplace-product-content.md) and the [`marketplace-product-content`](../skills/marketplace-product-content/SKILL.md) skill.
- For the paused product-file Issue workflow and its replacement by catalog/CLI flow, see [`marketplace-offer-update-workflow.md`](marketplace-offer-update-workflow.md); Odoo preparation is in [`odoo-first-publication.md`](odoo-first-publication.md).
- To export English Contentful application fields for the current `product_en.json` applications, see [`catalog-pull.md`](catalog-pull.md). To write reviewed metadata to Contentful drafts or publish it, see [`catalog-push.md`](catalog-push.md).
- Files such as `aliyun.json`, `aws.json`, `azure.json`, `huawei.json`, and `qcloud.json` contain existing task data. Check downstream consumers before editing and preserve their schemas.
- AI collaboration rules are in the root `AGENTS.md`; reusable workflows are in `skills/`.
- Reusable automation scripts live in the root `ci/` directory.
- Business commands use the `mk` CLI in `cli/`, separate from development `make` targets; `make cli` creates `.venv`, installs the CLI, and enters the `mk` command shell.
- To list marketplace product versions from cloud APIs, see [`marketplace-versions.md`](marketplace-versions.md). The initial implementation supports Aliyun China.
- Marketplace title/summary version extraction rules are in [`marketplace-version-extraction.md`](marketplace-version-extraction.md).
- Shared marketplace sources, platform URL templates, Websoft9 store homepages, and code routing live in `config/marketplace.json`; both `mk` and the Astro site read this file.
- The static Marketplace dashboard lives in `site/` (Astro): `/` is the overview, `/apps` is the application list, and `/apps/<key>` is the application detail page; pages read the marketplace data sources at build time.
- Application detail pages read use cases and keywords directly from `product_en.json`; they no longer depend on `data/app-metadata.json`.
- To query Aliyun products and check application image versions, use [`aliyun-product-freshness`](../skills/aliyun-product-freshness/SKILL.md).
- The scheduled and manually triggered multi-cloud product freshness entry point is documented in [`product-freshness-workflow.md`](product-freshness-workflow.md).
- The MCP client configuration is `.vscode/mcp.json`: GitHub uses remote OAuth, Context7 uses its remote service, and Playwright is launched with `npx`. Complete any authorization or dependency setup requested by the MCP client before use.
