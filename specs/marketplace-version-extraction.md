# Marketplace Version Extraction

## Inputs

- `title`: product title, shaped as `<trademark> <marketing text>`.
- `summary`: short description. Use only the text before the first comma (`,` or `，`); call it `head`.
- `app`: application name, taken from the title trademark by default.

## Rules

1. Normalize names case-insensitively, ignoring spaces and punctuation. A title name and a `head` name match when either contains the other, e.g. `Apache ActiveMQ` ≡ `ActiveMQ`.
2. An optional qualifier may follow the app name and is skipped case-insensitively: `CE`, `Community`, `Community Edition`.
3. After the app name (and skipped qualifier) there is exactly one space. The first token after it is the version when it:
   - contains a digit, e.g. `v7.1`, `V19`, `v2026-05`, `v3-core`, `v19/18/17/16`; or
   - is `latest`, `preview`, `preview latest`, or a compound containing `latest`/`preview`.
4. Output the version token verbatim, keeping a leading `v`/`V`.
5. Use an alias table for different trademarks that mean the same app, e.g. `Woocommerce` → `WordPress`.

## Algorithm

1. Take `head`.
2. Locate `app` in `head`, allowing name containment and the alias table.
3. Skip at most one qualifier.
4. Take the next space-delimited token; output it verbatim if it is a version.
5. If `head` fails, apply the same rule to `title`.
6. Otherwise output `未识别`.

## Must not

- Treat digits inside a trademark as a version: `TYPO3`, `Neo4j`, `Websoft9`.
- Treat plain words as versions: `solution`, `platform`, `pre-configured`, `community`.
- Accept a version attached directly to the trademark without a space (e.g. `Odoo19`).
- Guess a version that is not in the text.

## Examples

| App | Summary head | Version |
| --- | --- | --- |
| Apache ActiveMQ | ActiveMQ v6.3, ... | v6.3 |
| ONLYOFFICE Docs | ONLYOFFICE Docs CE v9, ... | v9 |
| Canvas | Canvas v2026-05 image | v2026-05 |
| GitLab | GitLab community v19 image | v19 |
| InfluxDB | InfluxDB v3-core image | v3-core |
| Woocommerce | WordPress v7.1 image | v7.1 |
| OpenDesign | OpenDesign preview-latest | preview-latest |
