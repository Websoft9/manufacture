# AI Collaboration Guide

## Before You Start

- Read `specs/README.md` and the relevant specifications first. Follow the repository's existing JSON, issue-template, and workflow conventions.
- Put reusable workflows in `skills/<skill-name>/SKILL.md` and list them in `skills/README.md`.
- Existing GitHub Actions may consume business data files such as cloud-platform JSON files. Do not change their schemas or reformat them in bulk unless requested.

## Execution Requirements

- Verify sources and current state before making changes. Use current platform/API data for products, versions, and marketplace status.
- Do not guess versions, product status, or field meanings. Mark unsupported conclusions as unverified.
- Before creating an issue, search for an equivalent or still-open issue. Create one only for confirmed differences and include concise, traceable evidence.
- Never write secrets, tokens, signed requests, or sensitive API responses to the repository, logs, issues, or replies. Read credentials from environment variables or secure MCP client inputs.
- Run the smallest relevant validation after changes and report its scope and any limitations.

## References

- Project specifications: `specs/`
- Reusable workflows: `skills/`
- Copilot repository instructions: `.github/copilot-instructions.md`
- Repository MCP client configuration: `.vscode/mcp.json`
