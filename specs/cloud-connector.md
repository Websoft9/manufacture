# Cloud Connector

## AWS 
GitHub Actions authenticates to AWS through GitHub OIDC and assumes a least-privilege IAM role, so no long-lived AWS access keys are stored in the repository. Trust policies must use this repository's immutable subject prefix `repo:Websoft9@36851177/marketplace@326841278` and allow only the intended branch or environment.

## Aliyun China Marketplace
The `aliyun` option in `.github/workflows/marketplace-offer-list.yml` uses GitHub OIDC to assume a RAM role. Set the `ALIYUN_ROLE_ARN` and `ALIYUN_OIDC_PROVIDER_ARN` GitHub Actions Variables. The workflow lists front-end-visible mirror products from `长沙网久软件有限公司` and extracts the application version from each product summary.

## Alibaba Cloud International Marketplace
The `alibabacloud` option reads the public Websoft9 store listing and shows image products with their detected application versions. It does not require cloud credentials.
