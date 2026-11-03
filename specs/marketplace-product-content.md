# Marketplace Product Content and AWS Metadata Updates

## Scope and ownership

Supports product expressiveness and transactionability through reusable master
data, personalized listing copy and AWS Catalog metadata updates. This initial
implementation supports **existing `AmiProduct@1.0` listings** and
`UpdateInformation`; creation, delivery-option/version updates, pricing, refunds
and visibility changes require their own platform workflows.

`data/offer/aws.md` remains the supplied writing example. Its Odoo title and
JupyterHub short description conflict; its version, hardening, rollback and SLA
claims are not automatically verified. The new Odoo record is explicitly a draft.

## Data model

| File | Responsibility |
| --- | --- |
| `data/offer/product.schema.json` | Versioned JSON Schema for application facts and AWS bindings |
| `data/offer/products/<key>.json` | Edition, shipped components, use cases, keyword candidates, evidence and platform configuration |
| `data/offer/provider.json` | Shared provider identity, console capabilities, support and trademark text, with separate verification |
| `data/offer/templates/aws-ami.json` | Fixed copy structure with named placeholders, no credentials or per-product IDs |
| `skills/marketplace-product-content/SKILL.md` | Fact checking and personalized content authoring procedure |

The schema uses `schemaVersion: 1`. Only the AWS AMI binding exists today;
future platforms must add explicit schemas/adapters rather than interpreting
AWS fields for other platforms. Existing cloud task JSON schemas are unaffected.

Application editions and versions are facts, not generated marketing assertions.
`application.versions` may be empty; version facts are not inserted into copy
automatically. `contentOverrides` provides literal, per-listing replacements for
the title/descriptions/highlights/keywords. Overrides inherit the record's
evidence requirements and need the same review as template-generated text.

Five verification blocks cover application, provider, listing identity,
deployment and commercial claims. `verified` requires a checked date and evidence;
the tool validates structure, not truth. The skill/operator checks the evidence.
All five must be verified before submission because deployment and billing
statements also appear in the long description. Unknown Catalog IDs stay null.

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

Existing entity values are read from `Description`, `PromotionalResources` and
`SupportInformation`; the read shape is not the update shape. Plans normalize
additional-resource `Type` fields before comparison. Empty/absent optional
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

For the Issue/Form and Actions user journey (compare, restricted editing or AI
optimization, review, publish and confirm), see
[`marketplace-offer-update-workflow.md`](marketplace-offer-update-workflow.md).
It reuses the renderer and revision-bound planner documented here.

Offline commands use the repository template and schema; JSON and Markdown
are printed to stdout and no source file is rewritten.

```sh
mk offer render --product data/offer/products/odoo.json --format markdown
mk offer validate --product data/offer/products/odoo.json
mk offer validate --product data/offer/products/odoo.json --publish-ready
python3 ci/validate_offers.py
```

`--provider` and `--template` allow alternate reviewed local source files. The
template ID must match the product record. Draft validation succeeds for the
Odoo example; `--publish-ready` fails until facts and identity are confirmed.

Install optional AWS dependencies and use AWS's normal credential provider
chain (SSO/profile, environment, or assumed role). Do not put credentials in
master data, command arguments, generated plans or repository configuration.

```sh
pip install '.[aws]'
mk offer list --profile marketplace-seller
mk offer plan --product data/offer/products/odoo.json --profile marketplace-seller
```

`list` resolves seller-owned AMI Catalog IDs with pagination. Set the verified
ID in the product's `entityId`; a public SKU, product code or `prodview-` ID is
not a substitute. The integration uses `us-east-1` for the Catalog client.

Save the **reviewed plan output** in an access-controlled location outside Git
(for example under `/tmp/opencode/` for a local trial), then submit exactly it:

```sh
mk offer apply --product data/offer/products/odoo.json --plan /tmp/opencode/odoo-plan.json --profile marketplace-seller --wait-seconds 600
mk offer status <change-set-id> --profile marketplace-seller --wait-seconds 600
```

`apply` is the explicit write action. It checks verified evidence, rereads live
metadata and compares the complete recomputed plan to the reviewed artifact.
Changed source/template/provider, live revision or plan payload fails closed.
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
