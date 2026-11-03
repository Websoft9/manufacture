# Cloud Connector

## AWS 
GitHub Actions authenticates to AWS through GitHub OIDC and assumes a least-privilege IAM role, so no long-lived AWS access keys are stored in the repository. Trust policies must use this repository's immutable subject prefix `repo:Websoft9@36851177/marketplace@326841278` and allow only the intended branch or environment.
