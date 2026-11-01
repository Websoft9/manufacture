# Manufacture

围绕着Marketplace上商品管理的一系列任务：镜像制作、上架、SKU更新等

## 生产方式

- 计划生产：以周为单位进行生产计划制定，然后拆解为生产任务
- 直接生产：计划外的临时、紧急生产任务

## AI Collaboration

- Repository guidelines and constraints: [`AGENTS.md`](AGENTS.md)
- Project overview and conventions: [`specs/`](specs/README.md)
- Repository-specific skills: [`skills/`](skills/README.md)
- VS Code MCP configuration: `.vscode/mcp.json` (GitHub MCP uses GitHub OAuth; Playwright MCP requires Node.js/npx)
- Scheduled and manually triggered product checks: [Marketplace Product Freshness workflow](.github/workflows/product-freshness.yml)
