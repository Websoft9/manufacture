# Marketplace Product Content and AWS Metadata Updates

## Scope and ownership

Supports product expressiveness and transactionability through reusable master
data, personalized listing copy and AWS Catalog metadata updates. This initial
implementation supports **existing `AmiProduct@1.0` listings** and
`UpdateInformation`; creation, delivery-option/version updates, pricing, refunds
and visibility changes require their own platform workflows.

`data/offer/aws.md` remains the supplied writing example. Its Odoo title and
JupyterHub short description conflict; do not use that historical example as
source data. Application and vendor content is maintained in its authoritative
source and rendered deterministically by the template. Do not repeat a
per-application fact audit for unchanged source data and template output.

## Data model

| File | Responsibility |
| --- | --- |
| `data/offer/product.schema.json` | Runtime schema for the catalog + AWS rule projection |
| `data/.catalog/catalog.json` | Temporary Contentful application facts; git-ignored and not authoritative |
| `data/offer/vendor.json` | Shared vendor identity, highlights, console capabilities, support and trademark text |
| `data/offer/templates/aws-ami.json` | Fixed copy structure with named placeholders, no credentials or per-product IDs |
| `cli/aws_marketplace.py` | AWS Marketplace adapter: field names/limits, read normalization, update request shape |
| `skills/marketplace-product-content/SKILL.md` | Fact checking and personalized content authoring procedure |

## Layered architecture

Keep three layers separate:

1. **Source metadata** — application facts, optional AWS binding/category/media
   fields come temporarily from `data/.catalog/catalog.json`; vendor statements
   and templates stay in the repository. None of these files need to mirror a
   cloud API hierarchy.
2. **Authoring template** — `aws-ami.json` controls copy structure, placeholders,
   SearchKeywords sources and default Learning resources. It is not an AWS payload.
3. **AWS adapter** — `cli/aws_marketplace.py` translates between the authoring
   model and AWS. It owns field names/limits, read normalization and the update
   request shape.

`cli/aws_marketplace.py` declares the field contract in `FIELD_SPECS`: read
path, write field, type, limits, and read transformations. `CONTENT_FIELDS`,
`FIELD_LIMITS`, `current_content()` and `to_update_document()` derive from this
contract. Tests assert that template fields stay inside the contract and that
the read/write shapes round-trip.

AWS-facing names are aligned at the adapter boundary: `ProductTitle`,
`ShortDescription`, `LongDescription`, `Highlights`, `SearchKeywords`,
`SupportDescription`, `Categories`, `LogoUrl`, `VideoUrls`,
`AdditionalResources`. The nested read shape is not copied into authoring data.

Template placeholders name their source explicitly:

- `{catalog.*}` — temporary Contentful application facts (for example
  `{catalog.name}`, `{catalog.version}`, `{catalog.includedComponentsText}`)
- `{vendor.*}` — vendor file, including indexed values such as
  `{vendor.highlights[0]}`
- `{aws.*}` — product AWS listing (for example
  `{aws.commercial.billingSummary}`)
- `{product.*}` — product record (for example `{product.key}`)

A whole field can be sourced from an array placeholder, for example
`"SearchKeywords": "{catalog.searchKeywords}"`. Templates that cannot express a
field inline may still use `fieldSources`. Missing paths fail rendering instead
of silently producing empty text. Application versions come from the configured
`apps-verson.json`; `includedComponents` is temporarily generated until the
catalog/content model provides it.

The read shape differs from the update shape:

- Read: `Description.*`, `PromotionalResources.LogoUrl/Videos/AdditionalResources`,
  `SupportInformation.Description`.
- Update: flat `UpdateInformation` fields, including `VideoUrls` and
  `SupportDescription`.
- Read-side `AdditionalResources` items include `Type`; update-side items use
  `Text`/`Url`. The adapter removes `Type` for comparison and does not add it to
  the update payload.
- `LongDescription` is assembled from template sections; it is not a source field.

The schema uses `schemaVersion: 1`. Only the AWS AMI binding exists today;
future platforms must add explicit schemas/adapters rather than interpreting
AWS fields for other platforms. Existing cloud task JSON schemas are unaffected.

Application versions are supplied by `apps-verson.json`; `edition` and
`valueProposition` are no longer required from the repository product files.
`contentOverrides` provides literal, per-listing replacements for the
title/descriptions/highlights/keywords and still needs review.

Contentful application data, vendor copy and the shared template are the sources
of truth. The tool validates structure and renders deterministically; it does
not maintain a per-application verification status. Correct source data when it
is missing or inconsistent. Unknown Catalog IDs stay null and block publication
until resolved.

## AWS field mapping

| Authored/rendered content | UpdateInformation field |
| --- | --- |
| Title | `ProductTitle` |
| Short description | `ShortDescription` |
| Ordered long-description sections | `LongDescription` |
| 1–3 feature callouts | `Highlights` |
| Intent-oriented keyword phrases | `SearchKeywords` |
| Approved support description | `SupportDescription` |
| Platform-selected category names | `Categories` |
| Public unsigned resource URLs | `LogoUrl`, `VideoUrls`, `AdditionalResources` |

`aws-ami.json` declares `SearchKeywords` via a direct placeholder and
`Highlights` via indexed `vendor.highlights` values. It does not update
`Categories`, `LogoUrl`, or `VideoUrls`. It provides two default Learning resources
(AdditionalResources): `<name> Image Guide by Websoft9` at
`support.websoft9.com/en/docs/<key>`, and `Install Websoft9 on AWS`. A product's
non-empty `listings.aws.additionalResources` overrides those defaults.
`SupportDescription` is the AWS Marketplace Support details field; the two
AdditionalResources entries are the Learning resources rows.

Existing entity values are read from `Description`, `PromotionalResources` and
`SupportInformation`; the read shape is not the update shape. The AWS adapter
normalizes `Videos` to `VideoUrls`, reads `SupportInformation.Description` as
`SupportDescription`, and removes read-side additional-resource `Type` fields
before comparison. Update payloads use `Text`/`Url` only for additional resources. Empty/absent optional
categories/media fields preserve existing AWS values; this version does not
implement explicit deletion of them. Categories must be confirmed AWS category
names (AWS also validates them). The local checker validates supported lengths,
keyword combined length, duplicates, URL safety and unresolved placeholders.
It cannot establish semantic correctness or AWS approval.

Deployment instructions and refund policy appear in JSON preview sections, not
the submitted ChangeSet. This avoids treating Usage/Refunds from the example as
`UpdateInformation` fields. The Markdown preview uses plain section headings;
inspect the actual marketplace rendering after a write.

## Commands

The former product-file Issue workflow is paused; see
[`marketplace-offer-update-workflow.md`](marketplace-offer-update-workflow.md).
Application facts now come from the temporary catalog, so a future Issue flow
must write to Contentful instead of a repository product file.

`build` writes the human-review preview; use `--output -` to print it instead.
`--publish-ready` fails without writing until required fields and Catalog identity
are present. The default version source is remote; pass a local `--versions` file
for a fully offline run. None of these commands contact AWS.

```sh
mk offer build --app odoo --cloud aws
mk offer build --app odoo --cloud aws --output /tmp/odoo-preview.md
mk offer build --app odoo --cloud aws --publish-ready
mk offer plan --app odoo --profile marketplace-seller --output /tmp/odoo-plan.json
python3 ci/validate_offers.py
```

`build` is offline and does not contact AWS. It writes
`data/.catalog/aws/<key>.json` by default (git-ignored) as a human-review preview
that mirrors the authoring template: resolved `content`,
`longDescriptionSections`, `target`, and `AdditionalResources`. AWS read/write
views and ChangeSet payloads remain internal program structures. `plan` remains
the live revision-bound step; `--output` saves the complete plan/request for
review and audit.

`--catalog`, `--versions`, `--vendor` and `--template` allow
alternate reviewed local source files. Defaults are
`data/.catalog/catalog.json`, the configured version source,
`data/offer/vendor.json` and the AWS template.

Install optional AWS dependencies and use AWS's normal credential provider
chain (SSO/profile, environment, or assumed role). Do not put credentials in
master data, command arguments, generated plans or repository configuration.

```sh
pip install '.[aws]'
mk offer resolve-entity --cloud aws --code <offer-code> [--code <offer-code> ...] --profile marketplace-seller
mk offer plan --app odoo --profile marketplace-seller
```

`resolve-entity` resolves seller-owned AMI Catalog IDs with pagination. Set the confirmed
`entityId` in the temporary catalog item; a public SKU, product code or
`prodview-` ID is not a substitute. The integration uses `us-east-1` for the
Catalog client.

Save the **reviewed plan output** in an access-controlled location outside Git
(for example under `/tmp/opencode/` for a local trial), then submit exactly it:

```sh
mk offer apply --app odoo --plan /tmp/opencode/odoo-plan.json --profile marketplace-seller --wait-seconds 600
mk offer status <change-set-id> --profile marketplace-seller --wait-seconds 600
```

`apply` is the explicit write action. It rereads live metadata and compares the
complete recomputed plan to the reviewed artifact.
Changed source/template/vendor, live revision or plan payload fails closed.
It submits only changed fields, uses the live `EntityId@RevisionId` and a
deterministic plan hash as `ClientRequestToken`. A no-op plan submits nothing.
Each product gets one ChangeSet; AWS locks the entity while it processes it.

`--wait-seconds` bounds polling. Timeout means the change is still in progress,
not that it was cancelled or failed. `apply` reads back metadata on success when
waiting; `status` only reports the ChangeSet status. Run `plan` again to verify
the desired values after an asynchronously completed submission. Failed or
cancelled terminal states produce a nonzero exit status. Store the plan hash,
source hash, ChangeSet ID and status output as the publishing audit trail.
Raw responses and detailed AWS error messages are not exported, only error codes.

`plan --current <fixture.json>` accepts an offline DescribeEntity-shaped fixture
for development. Do not check real seller API responses into Git. Offline plans
must still match a fresh live snapshot before `apply` will accept them.

## IAM and API boundaries

Read access needs `aws-marketplace:ListEntities`, `DescribeEntity` and
`DescribeChangeSet`. Write access needs `aws-marketplace:StartChangeSet` scoped
to the intended `AmiProduct` ARN and `ChangeSet/*` ARN, with the
`catalog:ChangeType` condition set to `UpdateInformation`. Do not use an
administrator policy for this workflow. SDK calls expose error codes only.

The API's `Intent: VALIDATE` is documented for adding single-AMI versions;
it is not a general dry-run for `UpdateInformation`. Local `validate` and
`plan` therefore perform no StartChangeSet call. AWS may reject content
asynchronously even after local validation passes.

MCP is optional. The official AWS MCP Server provides generic AWS API access,
but publication automation uses the deterministic SDK adapter here. A future
MCP wrapper should call the same render/plan/apply logic, preserving IAM and
revision checks rather than maintaining separate payload generation rules.

## Source references (checked 2026-11-03)

- [Seller products / UpdateInformation](https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/seller-products.html#update-information)
- [StartChangeSet](https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_StartChangeSet.html)
- [DescribeEntity](https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_DescribeEntity.html)
- [DescribeChangeSet](https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_DescribeChangeSet.html)
- [Catalog IAM access](https://docs.aws.amazon.com/marketplace/latest/developerguide/catalog-api-access-control.html)
- [AWS-maintained AMI shapes](https://github.com/awslabs/aws-marketplace-catalog-api-shapes-for-python)
- [Official AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)

AWS documentation and generated shapes can disagree (for example Sku limits);
unsupported fields are excluded from this adapter. Recheck documentation when
expanding its field/change-type scope.
