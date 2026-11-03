# Issue-driven marketplace content updates

## User journey

1. Create **更新应用商品信息** from New issue. Select the application and AWS,
   and describe the update goal. The dropdown lists master records, not all apps
   in the public catalog. Odoo is currently the only record and is still a draft.
2. The workflow posts current AWS values versus repository/template output,
   publication blockers, editable application copy and a full draft hash.
   Missing identity/data results in an actionable message, not guessed bindings.
3. Use a new Issue comment to edit or ask Copilot to optimize:

   ````text
   /offer edit
   ```json
   {"valueProposition": "Manage your business applications in your own AWS environment."}
   ```
   ````

   Or `/offer optimize Make the use cases concise without adding features`.
   Each command is one asynchronous turn. Ordinary discussion comments do not run
   AI. Invalid edits or AI results leave the previous draft intact.
4. Review the latest diff and facts, then comment `/offer approve <full-draft-hash>`.
   Unverified facts block approval. Editing/replanning clears the previous review.
5. Separately comment `/offer publish <full-draft-hash>`. The workflow rechecks
   repository inputs and live AWS revision before submitting exactly that plan.
6. `/offer status` queries the original ChangeSet and checks the metadata on
   success. Processing stays **发布中**; API success without matching values is
   **需处理：回读不一致**. No duplicate submission is needed to check status.
7. Once **待前台确认**, inspect the actual Marketplace page, then comment
   `/offer complete`. The workflow records the confirmer and closes the Issue
   with reason `completed`.

**Marketplace Offer Update** in Actions also accepts an existing Issue number
and the same command. It operates on that task; it does not create another Issue.
All operations require current repository write/maintain/admin permission.

## Editing boundary

Only `application.summary`, `valueProposition`, `useCases` and `searchKeywords`
are editable by this workflow, for humans and AI alike. JSON schema and rendered
AWS limits are revalidated. Fixed template structure, provider/support/trademark,
deployment/billing statements, identity, edition, components and versions cannot
be replaced. Records with `contentOverrides` are rejected by this entry point;
maintain their template structure in the repository first. Factual correctness
still requires human review; structural validation does not prove a claim true.

## State and recovery

- Status comments link each state to the producing workflow run and SHA-256 hash.
  The state is loaded only from `github-actions[bot]` comments and artifacts from
  this repository's `marketplace-offer-update.yml`, with an Issue binding check.
- Product snapshot, plan/diff, source hash, approval and ChangeSet ID are stored
  as the run's `offer-update-state` artifact for **30 days**, outside Git. Only
  supported metadata fields are exported; no raw seller API response is stored.
- `prepare` rereads repository and cloud data; `edit`/`optimize` regenerate the
  plan and invalidate approval. Source/revision changes require a fresh review.
- Submitted updates block edits/replanning until the original result is checked.
  `status` uses the submitted desired-content snapshot, even if repo data changes.
- There is no automatic polling schedule: use `/offer status` while processing.
  An interrupted run must be inspected before retrying publication; the original
  plan hash is the AWS idempotency token. Expired artifacts require manually
  checking any previous ChangeSet in AWS before starting another task.
- Draft edits remain task-local. The final artifact preserves the exact product
  snapshot for subsequent repository maintenance; the workflow does not silently
  overwrite master data. Before a later refresh, maintain accepted application
  copy in its master record to avoid proposing the old repository text again.

## Setup and scope

- Merge the workflow/form to the default branch. Configure `AWS_ROLE_ARN` and
  OIDC trust per `cloud-connector.md`; the role needs the read permissions and
  scoped `UpdateInformation` write permission in `marketplace-product-content.md`.
- Enable Copilot CLI in Actions (`copilot-requests: write`). Optional
  `COPILOT_CLI_TOKEN` follows the existing product-freshness workflow convention.
  AI runs without AWS/Issue-write credentials and with shell/write tools denied;
  output passes the same allowlist and validations as manual edits.
- Maintain verified master/provider data and seller Catalog EntityId before
  publication. Never mark facts verified just to unblock the workflow.
- When adding a product master record, add its `key` to the form's application
  dropdown. Platforms are intentionally limited to the implemented AWS adapter.
- This first operational journey updates existing AMI listing metadata. New AMI
  creation, image releases, pricing, visibility and other clouds need dedicated
  workflows; the existing new-offer Issue template remains their intake entry.

## Verification

`python3 -m unittest tests.test_offer ci.tests.test_offer_update`
tests the fixed/editable boundary, plan binding, review invalidation, submission
and asynchronous result handling using synthetic API fixtures. A live trial
requires a verified listing, configured GitHub/AWS permissions and explicit
publication authorization.
