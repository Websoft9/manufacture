# Issue-driven marketplace content updates

## User journey

1. Create **Update Marketplace Product** from New issue. Select the application
   and AWS, and describe the update goal. The form is English; the dropdown lists
   master records, not all apps in the public catalog. Odoo is currently the only
   record and is still a draft. The task is recognized by the
   `[Marketplace Offer Update]` title or, if the title is edited, by the form's
   `### Application` / `### Target platform` (or legacy Chinese) sections.
   The form itself documents that each follow-up action needs a new `/offer`
   comment; the form markdown is the user-facing command reference.
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

   Or `/offer optimize` to use the Issue's **Update goal**, or
   `/offer optimize Make the use cases concise without adding features`.
   Each command is one asynchronous turn. Ordinary discussion comments do not run
   AI. Invalid edits or AI results leave the previous draft intact.
4. Review the latest diff and facts, then comment
   `/offer approve <full-draft-hash>`. When the draft contains Issue-local copy
   edits, add `confirm`: `/offer approve <full-draft-hash> confirm`, explicitly
   attesting that no unverified factual claims were added. Unverified base facts
   still block approval. Editing/replanning clears the previous review.
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
Issue/comment operations require the actor's `author_association` to be
`OWNER`, `MEMBER` or `COLLABORATOR`; `workflow_dispatch` already requires write
access. For stricter publication control, require a protected `environment` or a
reviewer team before adding one here.

## Editing boundary

Only `application.summary`, `valueProposition`, `useCases` and `searchKeywords`
are editable by this workflow, for humans and AI alike. They feed the rendered
title, short description, long description, highlights and keywords; editing
those rendered fields directly is not supported. JSON schema and rendered AWS
limits are revalidated. Fixed template structure, provider/support/trademark,
deployment/billing statements, identity, edition, components and versions cannot
be replaced. Records with `contentOverrides` are rejected by this entry point;
maintain their template structure in the repository first.

Because these four fields are factual copy, editing them marks the draft as
Issue-edited. Approval then requires `confirm`, a human attestation that the
change did not add unverified facts. Base repository verification flags are not
silently rewritten. Factual correctness still requires human review; structural
validation does not prove a claim true.

## State and recovery

- Status comments link each state to the producing workflow run and SHA-256 hash.
  The state is loaded only from `github-actions[bot]` comments and artifacts from
  this repository's `marketplace-offer-update.yml`, with an Issue binding check.
- Product snapshot, plan/diff, source hash, approval and ChangeSet ID are stored
  as the run's `offer-update-state` artifact for **30 days**, outside Git. Only
  supported metadata fields are exported; no raw seller API response is stored.
- `prepare` rereads repository and cloud data and **discards Issue-local edits**;
  `edit`/`optimize` regenerate the plan and invalidate approval. Source/revision
  changes require a fresh review.
- While a ChangeSet is **发布中**, only `/offer status` is allowed. After a
  terminal **需处理：发布失败** or **需处理：回读不一致**, run `/offer prepare`
  to start a fresh draft and review; do not reuse the old ChangeSet. A
  **待前台确认** task must be completed first.
- Commands for one Issue are queued (`queue: max`) so rapid edit/approve
  comments are not dropped. Different Issues may run concurrently; the live
  revision and plan hash checks still make conflicting publications fail closed.
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
- Enable Copilot CLI in Actions (`copilot-requests: write`). Configure a
  dedicated `COPILOT_CLI_TOKEN` with the Copilot Requests permission; the
  workflow intentionally does not fall back to the broad `github.token`. Without
  it, `/offer optimize` fails with an actionable message while `edit`, `approve`
  and `publish` keep working.
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
tests the fixed/editable boundary, fact-confirmation gate, plan binding, review
invalidation, terminal-state recovery, member authorization, submission and
asynchronous result handling using synthetic API fixtures. A live trial requires
a verified listing, configured GitHub/AWS permissions and explicit publication
authorization.
