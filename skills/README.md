# Repository Skills

Repository-specific agent skills belong in `skills/<skill-name>/SKILL.md`. Use a lowercase kebab-case directory name and YAML `name` and `description` metadata. Each skill should specify its data sources, steps, stopping conditions, and expected output.

## Available Skills

- [Aliyun marketplace image version check](aliyun-product-freshness/SKILL.md): Check a supplier's published and visible image products and summarize outdated versions in one GitHub issue.

The [Marketplace Product Freshness workflow](../.github/workflows/product-freshness.yml) registers and invokes the selected skill. It can run on a schedule or be started manually from the repository's **Actions** tab.
