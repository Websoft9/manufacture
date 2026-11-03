# Cloud Connector

## AWS 
GitHub Actions authenticates to AWS through GitHub OIDC and assumes a least-privilege IAM role, so no long-lived AWS access keys are stored in the repository. Trust policies must use this repository's immutable subject prefix `repo:Websoft9@36851177/marketplace@326841278` and allow only the intended branch or environment.

## Aliyun China Marketplace
The `aliyun` option in `.github/workflows/marketplace-offer-list.yml` uses `aliyun/configure-aliyun-credentials-action` to request a GitHub OIDC token with audience `sts.aliyuncs.com` and assume RAM role `acs:ram::1904996544835414:role/Github-Action-Updater-Marketplace` through OIDC provider `acs:ram::1904996544835414:oidc-provider/github-actions-marketplace`. The role trust policy should match issuer `https://token.actions.githubusercontent.com`, audience `sts.aliyuncs.com`, and the repository's immutable `sub` for the allowed branch or environment. The workflow currently runs from `main` and does not use a GitHub Environment for this job; its expected subject is `repo:Websoft9@36851177/marketplace@326841278:ref:refs/heads/main`.

The role must have the minimum Market API permission required by `DescribeProducts`. OIDC credentials are temporary and are exported by the action for the following Python SDK step; do not configure long-lived Aliyun AccessKey secrets for this workflow.
