# Project Specifications (AI Quick Start)

- This repository manages Websoft9 marketplace product production and maintenance tasks. Existing platform data and issue workflows are core business assets.
- The business positioning and scope are defined in [`business-positioning.md`](business-positioning.md).
- Files such as `aliyun.json`, `aws.json`, `azure.json`, `huawei.json`, and `qcloud.json` contain existing task data. Check downstream consumers before editing and preserve their schemas.
- AI collaboration rules are in the root `AGENTS.md`; reusable workflows are in `skills/`.
- Reusable automation scripts live in the root `ci/` directory.
- Business commands use the `mk` CLI in `cli/`, separate from development `make` targets; `make cli` creates `.venv`, installs the CLI, and enters the `mk` command shell.
- To list marketplace product versions from cloud APIs, see [`marketplace-versions.md`](marketplace-versions.md). The initial implementation supports Aliyun China.
- Shared marketplace sources, platform URL templates, Websoft9 store homepages, and code routing live in `config/marketplace.json`; both `mk` and the Astro site read this file.
- The static Marketplace dashboard lives in `site/` (Astro): `/` is the overview and `/apps` is the application list; both read the marketplace data sources at build time.
- To query Aliyun products and check application image versions, use [`aliyun-product-freshness`](../skills/aliyun-product-freshness/SKILL.md).
- The scheduled and manually triggered multi-cloud product freshness entry point is documented in [`product-freshness-workflow.md`](product-freshness-workflow.md).
- The MCP client configuration is `.vscode/mcp.json`: GitHub uses remote OAuth, Context7 uses its remote service, and Playwright is launched with `npx`. Complete any authorization or dependency setup requested by the MCP client before use.
