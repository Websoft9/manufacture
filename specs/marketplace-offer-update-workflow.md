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
