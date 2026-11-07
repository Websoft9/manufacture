# Catalog push to Contentful

`mk catalog push` writes English application metadata from a JSON dataset to
Contentful through the **Management API**. It updates existing `product` entries
matched by their `key` field. It does not create entries, delete entries, change
content models or edit assets.

## Credentials

Push uses a Contentful **Management API token**, not the Delivery/Preview token
used by `catalog pull`:

```sh
export CONTENTFUL_SPACE_ID=...
export CONTENTFUL_TOKEN=...              # CFPAT- Management API token
```

The same `CONTENTFUL_TOKEN` variable is used by pull and push. Push requires a
Management token (`CFPAT-`); a Delivery/Preview token cannot write and returns
HTTP 401. The token is sent in the `Authorization` header and is never printed.

## Usage

```sh
# Preview changes; no Contentful writes
mk catalog push --apps wordpress,odoo --dry-run --verbose

# Update drafts only
mk catalog push --apps wordpress,odoo

# Update and publish
mk catalog push --apps wordpress,odoo --publish
```

`--input` defaults to `data/.catalog/catalog.json` (git-ignored). Set
`MK_CATALOG_DIR` to use another directory. It accepts the object produced by
`catalog pull` (`items`), a bare JSON array, or `-` for stdin. `--apps` defaults
to every item in the input and preserves the requested order. Single-app and
multi-app data use the same file shape; only the number of `items` changes.

## Field mapping and merge

| Input field | Contentful field | Scope |
| --- | --- | --- |
| `id` | `key` | Lookup only; never updated |
| `trademark` | `trademark` | `--locale` (default `en-US`) |
| `overview` | `overview` | `--locale` |
| `keywords` | `keywords` | `--locale` |
| `usecases` | `useCases` | Non-localized |
| `components` | `Component` | Non-localized |
| `summary` | `summary` | `--locale` |
| `hasenterprise` | `hasEnterprise` | Non-localized |

The field IDs and localization flags come from the Contentful content-type
schema. The full entry is fetched first and only the target locale/fields are
merged; other locales, `tags`, references and unknown fields are preserved.
Input fields outside the table are rejected instead of silently ignored.

## Empty values and clearing

Empty strings, empty arrays and `null` are skipped by default. This prevents a
`pull` dataset containing `"usecases": []` from clearing a populated field.
Boolean `false` is a real value and is written. Use `--clear` to explicitly
write `""` for text fields, `[]` for array fields or `false` for Boolean fields.

## Safety and reporting

- Entry lookup is filtered by the selected application keys (`fields.key` /
  `fields.key[in]`), so a push for a few apps does not fetch the whole product
  table.
- Only entries whose target values differ are written.
- Updates send the fetched entry's `X-Contentful-Version`; a concurrent edit
  returns HTTP 409 and is reported instead of overwritten.
- Default behavior updates **drafts**. `--publish` publishes each successfully
  updated entry using the new draft version. It cannot be combined with
  `--dry-run`.
- `--allow-missing` skips input applications absent from Contentful; otherwise
  they are errors.
- The command continues through independent application errors and exits
  non-zero if any occurred. Summary counts and per-app details go to stderr;
  `--verbose` shows changed field names.
- `--progress` shows schema/entry pagination progress; `--no-progress` disables it.

## Limitations

- English locale only per invocation (`--locale`).
- Existing `product` entries only; no create/delete.
- `tags` and other linked fields are intentionally not pushed.
- Factual accuracy is not validated; the input dataset must be reviewed.

## Validation

```sh
python3 -m unittest tests.test_catalog_push
```

Tests use mocked Management API responses. A live push requires a Management API
token with write access to the product entries. A Delivery token cannot perform
this operation.
