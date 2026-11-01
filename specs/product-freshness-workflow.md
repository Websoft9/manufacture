# Marketplace Product Freshness Workflow

- Entry point: `.github/workflows/product-freshness.yml`, available from the repository's **Actions** tab after it is merged to the default branch.
- Schedule: Mondays at 08:21 China Standard Time (`00:21 UTC`). GitHub Actions schedules are best-effort and may start later.
- Manual run: choose `all`, `alibabacloud`, `azure`, `aws`, `huaweicloud`, or `googlecloud`. `all` runs only platforms whose skill files are present. A directly selected platform without a skill fails with an actionable message.
- Each configured platform runs as an independent matrix job and can create at most one issue, only when that platform's skill confirms outdated products.
- Add future cloud support by adding its skill under `skills/`, adding its platform-to-skill mapping in `scripts/resolve_product_freshness.py`, adding the platform to the workflow input choices, and mapping any required Actions secrets into the job environment.
- Alibaba Cloud requires Actions secrets `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`; add `ALIBABA_CLOUD_SECURITY_TOKEN` when using STS credentials. GitHub issue access uses the automatically provided `GITHUB_TOKEN` with `issues: write`. Copilot CLI requires `copilot-requests: write` and the organization policy to allow Copilot CLI usage in Actions.
