---
name: marketplace-product-content
description: Create or refresh personalized AWS AMI marketplace listing content from the temporary Contentful catalog, vendor policy, AWS listing rules and the shared AWS template. Use when drafting product pages or preparing a metadata update plan.
---

# Marketplace Product Content

## Goal and scope

The repository owns templates, vendor statements and AWS listing rules.
Application facts are **not** stored in the repository; they are pulled
temporarily into `data/.catalog/catalog.json` and remain authoritative in
Contentful.

## Data sources

- `specs/marketplace-product-content.md`.
- `data/.catalog/catalog.json` — temporary Contentful application facts.
- Optional AWS fields in the catalog item: `entityId`, categories, media,
  additionalResources and content overrides.
- `data/offer/vendor.json` (including `highlights`),
  `data/offer/templates/aws-ami.json`.
- `cli/aws_marketplace.py` for AWS names, limits and read/update shape.
- Version source from `config/app.json` (`apps-verson.json`).
- Official upstream documentation and actual image/deployment evidence.
- Seller-authorized Catalog API data via `mk offer resolve-entity` / `mk offer plan`.
- `data/offer/aws.md` is a historical example, not a source of truth.

## Procedure

1. Pull the target application:
   `mk catalog pull --apps <key>` (default `data/.catalog/catalog.json`).
   If the item is missing or wrong, correct Contentful and pull again. Do not
   create a repository product file.
2. Read optional AWS fields from the catalog item. Do not create a per-app AWS
   file or copy application facts into the repository.
3. If source data is missing, inconsistent, or conflicts with the approved
   listing, correct the authoritative Contentful/vendor/template source. Do not
   maintain a second per-application verification checklist.
4. Build and validate:
    `mk offer build --app <key> --cloud aws --output /tmp/<key>-preview.md`;
    use `--publish-ready` to check required source fields and Catalog identity.
    Review the rendered preview and AWS diff when approving the specific change,
    not as a repeat fact-verification exercise.
5. Use namespace-qualified placeholders that map directly to source fields:
   `{catalog.trademark}`, `{catalog.summary}`, `{catalog.usecases}`,
   `{catalog.keywords}`, `{versions.version}`, and `{vendor.*}`.
   `SearchKeywords` uses the whole array placeholder
   `{catalog.keywords}`; `Highlights` uses `{vendor.highlights[0..]}`.
   Arrays rendered into text use the explicit `join` filter. `components` is
   inserted before the fixed Nginx/Docker text; an optional second `join`
   argument supplies a suffix only for non-empty lists. Multi-version
   applications use the `Choose from ... at launch` short description with every
   configured version except `latest`; single-version applications use
   `Deploy ...`. `ShortDescription` does not vary by `catalog.hasenterprise`; the
   edition distinction stays in the long description and pricing copy. In the
   long description, true `hasenterprise` names the offer as
   `<app> Community Edition`, while false omits the edition label.
   Long-description section headings use Markdown bold when the template enables
   `boldLongDescriptionHeadings`; structured preview headings stay plain. Do not
   bypass fixed sections with `contentOverrides` unless explicitly reviewed.
6. Use version data from `apps-verson.json` through `{versions.version}`.
   Missing namespaces or fields fail rendering; there is no runtime product
   schema or fallback field mapping.
7. Build a template-shaped review preview:
   `mk offer build --app <key> --cloud aws` → `data/.catalog/aws/<key>.json`.
   It does not contact AWS and is not a submit-ready ChangeSet. The default
   version source is remote; pass a local `--versions` file for a fully offline run.
8. Run `mk offer plan --app <key> --profile <seller-profile> --output <path>` and
   review the exact `diff`, EntityId, revision and blockers. Save the plan outside
   Git as an access-controlled artifact.
9. Submit only the reviewed plan with `mk offer apply --app <key> --plan <path>
   --profile <seller-profile>`; then use `mk offer status` or `--wait-seconds`.
    Publication requires required source fields, a resolved Catalog EntityId and
    an explicitly reviewed plan.

The former product-file Issue workflow is paused. A future Issue flow must write
application facts to Contentful, not to `data/offer/products`.

## Stopping conditions

- Stop publication if identity, edition, components or material claims conflict.
- Missing required facts or Catalog identity block publication.
- Stop if credentials, catalog data or current seller entity are unavailable.
- Refuse stale/modified plans; regenerate rather than removing checks.
- Usage instructions, versions, refunds, pricing and visibility are previews or
  separate Catalog change types, not `UpdateInformation` fields.

## Expected output

- Temporary catalog data refreshed from Contentful.
- Updated AWS listing rules, not application facts.
- Rendered preview, validation report and remaining blockers.
- Offline `build` document when requested.
- Revision-bound plan/request and, for requested publication, ChangeSet ID,
  terminal status/error codes and read-back result.
