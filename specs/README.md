# Project Specifications (AI Quick Start)

- This repository manages Websoft9 marketplace product production and maintenance tasks. Existing platform data and issue workflows are core business assets.
- Files such as `aliyun.json`, `aws.json`, `azure.json`, `huawei.json`, and `qcloud.json` contain existing task data. Check downstream consumers before editing and preserve their schemas.
- AI collaboration rules are in the root `AGENTS.md`; reusable workflows are in `skills/`.
- To query Aliyun products and check application image versions, use [`aliyun-product-freshness`](../skills/aliyun-product-freshness/SKILL.md).
- The scheduled and manually triggered multi-cloud product freshness entry point is documented in [`product-freshness-workflow.md`](product-freshness-workflow.md).
- The MCP client configuration is `.vscode/mcp.json`: GitHub uses remote OAuth, Context7 uses its remote service, and Playwright is launched with `npx`. Complete any authorization or dependency setup requested by the MCP client before use.
