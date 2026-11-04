# Marketplace Product Versions CLI

`mk versions` reads application product codes from `https://artifact.websoft9.com/cloud_data/offer.json`, queries the selected cloud's product API, and prints product name, application ID, code, and the version found in the product summary.

## Aliyun China

Install the optional SDK dependency:

```sh
pip install '.[aliyun]'
```

Configure credentials in the environment. For STS credentials, set all three variables:

```sh
export ALIBABA_CLOUD_ACCESS_KEY_ID='...'
export ALIBABA_CLOUD_ACCESS_KEY_SECRET='...'
export ALIBABA_CLOUD_SECURITY_TOKEN='...' # only for STS
```

Run:

```sh
mk versions --platform aliyun
mk versions --platform aliyun --format csv
```

For local testing, `--offer` accepts a JSON file path. `--timeout` controls the HTTP timeout. The command currently supports only Aliyun China; other platform keys fail with an explicit unsupported-platform message until their APIs are implemented.

The Aliyun integration uses Market API `2015-11-01` `DescribeProduct` for each code. It reads `Name` and `ShortDescription`; the version is extracted only when a version-like token occurs in the summary in the context of the application/product name. If no such match exists, the output reports `未识别` rather than inferring a version from unrelated text such as the OS version.

## Offer List target versions

The Marketplace Offer List reads target application versions from `sources.versions` in `config/marketplace.json` (the `apps-version.json` source keyed by application ID). Product codes are mapped to application IDs through `offer.json`; a product without a unique mapping shows `-` instead of guessing a target version.

The Offer List also shows the first sentence of the product short description and an update suggestion. The suggestion compares Offer Version with Target Version: a newer target produces `Update to <version>`, an older target produces `Check target (<version>)`, an equal version produces `Up to date`, and missing/unparsable values produce `-`.
