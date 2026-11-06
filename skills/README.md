# Repository Skills

Repository-specific agent skills belong in `skills/<skill-name>/SKILL.md`. Use a lowercase kebab-case directory name and YAML `name` and `description` metadata. Each skill should specify its data sources, steps, stopping conditions, and expected output.

## Available Skills

- [Marketplace product content](marketplace-product-content/SKILL.md): Author personalized AWS AMI listing content from the temporary Contentful catalog, vendor policy and AWS listing rules, validate drafts, and prepare revision-bound Catalog API metadata updates.

- [Application content generation](app-content-generation/SKILL.md): Generate and update marketplace keywords, use cases, overview, and summary for a specified application in `catalog.json`.
- [Aliyun marketplace image version check](aliyun-product-freshness/SKILL.md): Check a supplier's published and visible image products and summarize outdated versions in one GitHub issue.
- [Marketplace search visibility](marketplace-search-visibility/SKILL.md): Search a marketplace for keywords and report whether and where Websoft9 products appear. Preliminary framework.
- [Product expressiveness](product-expressiveness/SKILL.md): Check a marketplace product's expression and compliance evidence, such as demo images, videos, cases, qualifications, and versions. Preliminary placeholder.

The [Marketplace Product Freshness workflow](../.github/workflows/product-freshness.yml) registers and invokes the selected skill. It can run on a schedule or be started manually from the repository's **Actions** tab.
