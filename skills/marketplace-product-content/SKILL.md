---
name: marketplace-product-content
description: Create or refresh personalized AWS AMI marketplace listing content from verified application facts, provider policy and the shared AWS template. Use when drafting product pages or preparing a metadata update plan.
---

# Marketplace Product Content

## Goal and scope

Maintain one master-data file per application under `data/offer/products/`,
render personalized AWS AMI content, and prepare a traceable metadata update.
This implements product expressiveness and transactionability. It complements
`app-metadata` (site use cases/keywords) and `product-expressiveness` (assessment).

## Data sources

- `specs/marketplace-product-content.md` and `data/offer/product.schema.json`.
- `data/offer/provider.json`, `data/offer/templates/aws-ami.json`.
- Current Websoft9 application catalog from `config/marketplace.json`.
- `data/app-metadata.json` as a draft use-case/keyword input, not factual proof.
- Official upstream documentation for edition-specific features and licensing.
- Actual published image/build manifest and deployment verification records.
- Seller-authorized Catalog API data via `mk offer list` and `mk offer plan`.
- Approved Websoft9 support, billing and trademark policies.
- `data/offer/aws.md` is a historical writing example, not a verified source.

## Procedure

1. Read the existing master record and schema. Match the application `key` to
   the catalog and identify the exact edition and AWS listing. A public SKU,
   `prodview-` page identifier or AMI product code is not the Catalog EntityId.
   Resolve the Catalog EntityId using `mk offer list --profile <seller-profile>`.
2. Check sources before writing. Record evidence and `checkedAt` separately for
   application, provider, listing identity, deployment and commercial facts.
   Mark `verified` only after checking each relevant claim. Do not promote
   draft site metadata or the supplied example to verified evidence.
3. Create `data/offer/products/<key>.json` using the Odoo record as the structural
   example. Preserve unknown fields as allowed null/empty values. Only list
   actually shipped components and versions. An upstream release alone is not
   proof that the image contains it. Versions are stored as facts and are not
   automatically injected into titles or keywords.
4. Personalize the application facts:
   - Summary: what the selected edition actually provides.
   - Value proposition: one specific, buyer-oriented benefit.
   - Use cases: practical workflows for this application, edition and deployment.
   - Keywords: prioritize user intent and feature terms. AWS already indexes
     product name, seller name and categories; don't duplicate them routinely.
     Use 1–15 phrases, <=50 characters each and <=250 combined characters.
   - Distinguish installed software from templates available for later deployment.
   - Do not substitute every occurrence of an old app name in a copied page.
5. Use the shared template for section order and common provider statements.
   Set `contentOverrides` only for a genuine product-specific need. A complete
   override is literal text, not another template. Keep support, trademark and
   billing statements consistent with their approved facts. Changes to shared
   provider text require rechecking every affected application's rendered output.
6. Run `mk offer render --product <file> --format markdown` and inspect every
   section. Check cross-product names, edition boundaries, unsupported versions,
   component lists, SLA wording and deployment instructions. Remove unsupported
   “hardened”, “ready in minutes”, “official”, “no lock-in” or rollback claims
   unless specific evidence supports them for this product.
7. Run `mk offer validate --product <file>` while drafting, and
   `mk offer validate --product <file> --publish-ready` before a publish plan.
   Fix the source/override if limits fail; do not silently truncate words.
8. Run `mk offer plan --product <file> --profile <seller-profile>` and review
   the exact `diff`, affected EntityId, revision and evidence. Record the plan
   as an access-controlled artifact outside the repository. No raw SDK responses,
   signed URLs, credentials or private offer terms belong in this repository.
9. Submit the reviewed plan only when the user requests publication using
   `mk offer apply --product <file> --plan <plan-file> --profile <seller-profile>`.
   This is an actual write: do not call it as a validation/dry-run operation.
   Poll `mk offer status <change-set-id>` or use `apply --wait-seconds 600`.
   The latter reads back the metadata after success. On failure, inspect error
   codes, correct data, regenerate the plan and review again.

## Stopping conditions

- Stop publication if identity, edition, components or material claims conflict.
- Missing/unverified facts allow a labeled draft, never a publish-ready record.
- Stop if credentials or current seller entity are unavailable; do not infer IDs.
- Refuse stale/modified plans and regenerate rather than removing revision checks.
- Usage instructions, security groups, AMI versions, refund terms, pricing and
  visibility are previews/reference facts here. They need dedicated Catalog
  change types and are not published by this metadata command.

## Expected output

- Updated product master record, with source evidence and verification states.
- Rendered listing preview with product-specific use cases and benefit wording.
- Validation report and remaining publication blockers.
- Metadata diff/plan when an authorized current entity is available.
- For requested publication: ChangeSet ID, terminal status/error codes and
  read-back result. “SUBMITTED” is not a successful published update.
