# Issue-driven offer updates (paused)

The former product-file Issue workflow is **paused** after moving application
facts out of the repository.

Historical status:

- Application facts now come temporarily from
  `data/.catalog/catalog.json`; the repository no longer stores
  `data/offer/products/`.
- Repository files own templates, vendor statements and AWS listing rules.
- The old workflow edited product JSON in a PR and is incompatible with this
  source model. Its workflow, Issue form and implementation were removed.
- A future Issue workflow must write application facts to Contentful, not to a
  repository product file.

Offline AWS offer work currently uses:

```sh
mk offer build --app odoo --cloud aws
mk offer plan --app odoo --profile marketplace-seller --output /tmp/odoo-plan.json
```

`build` writes `data/.catalog/aws/odoo.json`. `plan` remains live,
revision-bound and is the only step that prepares a submit-ready ChangeSet
request. Publication requires required source fields, a resolved Catalog
EntityId and an explicitly reviewed plan.

## Manual GitHub Actions apply workflow

`.github/workflows/marketplace-offer-apply.yml` runs manually for one
application and one cloud. Inputs are the catalog application id, an optional
display name used for the run label, and a cloud selector (currently only
`aws`). It does not publish files committed under `data/.catalog/<cloud>/`;
that directory is git-ignored. The workflow builds the preview there, generates
a live revision-bound plan, uploads the plan and source snapshots as artifacts,
then waits for approval on the `<cloud>-marketplace-production` environment
before running `mk offer apply`.

Required repository configuration:

- Secret `CONTENTFUL_TOKEN`.
- Variable `CONTENTFUL_SPACE_ID`; optional variable `CONTENTFUL_ENVIRONMENT`
  (default `master`).
- Variable `AWS_PLAN_ROLE_ARN` for read-only planning, or reuse `AWS_ROLE_ARN`.
- Protected environment `<cloud>-marketplace-production` (currently
  `aws-marketplace-production`) with required reviewers, optional self-review
  prevention and a `main` branch restriction.
- Environment variable `AWS_APPLY_ROLE_ARN` with write access to
  `DescribeEntity` and `StartChangeSet` for the target AMI product.

The plan job uses read-only credentials. The apply job starts only after
environment approval, rechecks source snapshots and live revisions, and fails
closed if either changed. The reviewed artifact contains
`catalog.json`, `apps-verson.json`, `preview.json` and `plan.json`.
