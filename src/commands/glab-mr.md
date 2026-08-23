---
description: Draft and optionally publish a GitLab merge request for the current branch
---

# Task

Draft and optionally publish a GitLab merge request for the current branch.

This command runs after commits already exist.

You must:

1. Analyze committed changes on the current branch.
2. Use the latest commit message as context.
3. Extract the issue number and fetch issue details with `glab`.
4. Detect whether a merge request already exists for the branch.
5. Draft exactly one merge request title and one merge request description.
6. Present the draft to the user and request explicit approval before any
   `glab mr create` or `glab mr update` command is executed.
7. If the user approves, execute the appropriate `glab` command.
8. If the user does not approve, provide the exact `glab` command without
   executing it.

You must never:

- publish a merge request without explicit user approval
- guess or invent an issue number
- ignore required merge request template content when a template is in use
- overwrite an existing merge request blindly when the target merge request is
  ambiguous

---

# Execution Workflow

Follow these steps in order.

## Step 1: Verify repository context

Run:

```bash
git rev-parse --is-inside-work-tree && git branch --show-current && git status --short
```

If not inside a Git repository, or if the branch name is empty:

STOP.

Tell the user:

- no valid Git repository context was found
- they should run the command from the repository and branch they want to open
  the merge request for

Do not continue.

---

## Step 2: Verify `glab` availability and authentication

Load the `glab` skill before this step. Follow it for install, authentication,
host selection, repository targeting, and troubleshooting branches. Keep the
exact command sequence in this file as the workflow source of truth.

Run:

```bash
glab --version && glab auth status
```

If `glab` is missing, authentication fails, or the host is wrong:

STOP.

Tell the user:

- `glab` is not ready for merge request operations
- they should resolve install or auth first

Do not continue.

---

## Step 3: Determine branch, upstream remote, and target branch

Run commands equivalent to these:

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git remote show <upstream-remote>
```

Determine:

1. current branch
2. upstream branch
3. upstream remote name
4. default target branch for that remote

If the branch has no upstream:

STOP.

Tell the user:

- current branch is not pushed to a remote upstream
- they should push the branch first so the merge request can target it

Do not continue.

Do not assume the remote is named `origin`.

Derive the remote name from the upstream branch first. Then determine the
remote default branch from that remote.

If the default target branch cannot be determined reliably:

STOP.

Ask the user which target branch to use.

Never guess the target branch.

---

## Step 4: Determine issue number

First run:

```bash
git branch --show-current
```

Extract the issue number from the branch name.

Recognize common formats:

- `123-description`
- `issue-123-description`
- `feature/123-description`
- `fix/123-description`
- `#123`

If branch parsing fails, run:

```bash
git log -1 --pretty=%B
```

Extract the issue number from the latest commit footer.

Recognize footer patterns such as:

- `Fixes #123`
- `Implements #123`
- `Closes #123`

The issue number is mandatory.

If an issue number still cannot be found:

STOP.

Ask the user for the issue number.

Never:

- guess an issue number
- invent an issue number
- proceed without issue context

---

## Step 5: Gather authoritative context

Collect repository and change context.

Also detect whether the current branch contains commits not yet present on the
target branch.

Run commands equivalent to these:

```bash
git log -1 --pretty=%B
git log --reverse --format='%H%n%s%n%b%n---' <target-branch>..HEAD
git diff --stat <target-branch>...HEAD
git diff --name-only <target-branch>...HEAD
glab issue view <issue-number> --output=json
glab mr list --source-branch "<current-branch>" --output=json
```

Use the commit log, diff stat, and changed-file list as the first-pass context.
Inspect the full patch only when those sources leave important reviewer-facing
details ambiguous.

Use the current repository as the default `glab` target unless explicit `-R`
is needed.

If the issue fetch fails:

STOP.

Tell the user:

- the issue context could not be retrieved from GitLab
- merge request drafting requires valid issue context

Do not continue.

If there are no commits or no diff between `<target-branch>` and `HEAD`:

STOP.

Tell the user:

- no merge request content was found for the current branch
- the branch may already be fully merged or contain no effective changes

Do not continue.

---

## Step 6: Detect merge request mode

From the merge request lookup, determine one of these modes:

1. create mode: no merge request exists for the current branch
2. update mode: exactly one merge request exists for the current branch

If multiple merge requests are returned for the source branch:

STOP.

Ask the user which merge request should be updated.

Do not continue until the target merge request is explicit.

If update mode is selected, fetch the current merge request title and
description before drafting so existing human-written context can be preserved
or intentionally replaced.

Run a command equivalent to:

```bash
glab mr view <mr-reference> --output=json
```

---

## Step 7: Detect merge request template

Inspect repository templates under:

```text
.gitlab/merge_request_templates/
```

Rules:

1. If no template files exist, proceed without a repository template.
2. If exactly one template exists, use it as the base template.
3. If multiple templates exist and one is clearly named `default.md` or
   `Default.md`, use that file as the base template.
4. If multiple templates exist and no default is clear:

   STOP.

   Ask the user which template to use.

When a template is used:

- preserve required headings and checklist items
- keep the template structure as the base contract
- fill the template with change-specific content rather than replacing it

---

## Step 8: Draft title and description

Generate exactly one merge request title and one merge request description.

### Source precedence

Use this precedence order:

1. repository template requirements
2. issue ticket facts from GitLab
3. existing merge request body and title when in update mode
4. latest commit message
5. commit range across `<target-branch>..HEAD`
6. actual diff and changed files

### Title requirements

- concise and specific
- reflects the primary user-visible or workflow-visible change
- should align with the issue intent and latest commit message
- no unnecessary prefix such as `WIP:` unless the branch is clearly not ready

### Description requirements

The description must:

- explain why the change exists
- summarize what changed
- call out notable implementation decisions when they matter to reviewers
- mention testing or validation evidence when available
- preserve repository template sections when a template exists
- preserve still-correct human-authored content from the existing merge request
  when in update mode unless the user clearly wants replacement
- remain readable in GitLab markdown

Avoid:

- raw diff dumps
- boilerplate that says nothing specific
- diagrams that are more complex than the change they explain

### Diagram policy

Use a Mermaid diagram only when it improves reviewer clarity more than bullets
or a compact table would.

Include a diagram when the change affects request flow, control flow, state
transitions, pipeline stages, or interactions between multiple components, and
that flow can be grounded in the patch and supporting context.

Omit the diagram when it would only restate nearby prose or when no meaningful
interaction or flow can be inferred confidently.

If a diagram is included:

- render exactly one fenced `mermaid` code block
- use `sequenceDiagram` for ordered interactions or event flow
- use `flowchart TD` for branching logic or lifecycle flow
- keep it small, grounded, and reviewer-oriented
- do not invent actors, services, calls, or state changes not supported by the
  patch or review context

### Built-in description shape

If no repository template exists, use this default structure:

```markdown
## Summary

## Why

## What Changed

## Flow / Logic

## Testing

## Risk / Rollback
```

You may omit a section only when there is truly no meaningful content for it.

---

## Step 9: Quality gate

Before showing the draft, verify:

- issue number is present and real
- title matches issue and committed work
- description reflects the actual commit range and diff
- repository template requirements are preserved when applicable
- any Mermaid diagram is justified and small
- no command execution has occurred yet

If any rule is violated, fix the draft before continuing.

---

## Step 10: Present draft and request approval

Show the user:

1. mode (`create` or `update`)
2. target branch
3. issue number
4. proposed title
5. proposed description
6. exact `glab` command that would be executed

Then ask explicit approval using the question tool.

Use options equivalent to:

- `Yes, run glab`
- `No, return command only`
- `Cancel`

If the answer is `Cancel`:

STOP.

Return the draft and state that no command was executed.

If the answer is `No, return command only`:

Do not execute `glab`.

Return the draft and exact command only.

If the answer is `Yes, run glab`:

Continue to Step 11.

Never continue to Step 11 without explicit approval.

---

## Step 11: Execute the publish command

Use the detected mode.

### Create mode

Execute `glab mr create` with the generated title and description.

Publish the exact title and description that were shown to the user for
approval. Do not ask GitLab CLI to apply a second template during publish if
that would change the reviewed draft.

### Update mode

Execute `glab mr update` for the existing merge request with the generated
title and description.

Use a shell-safe command that preserves newlines in the description.

Preferred pattern:

```bash
DESCRIPTION=$(cat <<'EOF'
<full description>
EOF
) && glab mr create --target-branch '<target-branch>' --title '<title>' --description "$DESCRIPTION"
```

or, for updates:

```bash
DESCRIPTION=$(cat <<'EOF'
<full description>
EOF
) && glab mr update <mr-reference> --title '<title>' --description "$DESCRIPTION"
```

If execution fails:

- report the exact failure briefly
- provide the exact command that failed
- do not claim the merge request was created or updated

If execution succeeds:

- capture the merge request URL or identifier from command output
- report success clearly

---

# Output Format

Return only:

### 1. Mode and target

```text
Mode: <create|update>
Target branch: <target-branch>
Issue: #<issue-number>
```

### 2. Merge request title

```text
<title>
```

### 3. Merge request description

```markdown
<description>
```

### 4. GitLab command

```bash
<exact glab command>
```

### 5. Status

If the user did not approve execution:

```text
Not executed.
```

If the user approved execution and the command succeeded:

```text
Executed successfully: <mr-url-or-reference>
```

If the user approved execution and the command failed:

```text
Execution failed: <brief exact failure>
```

Return no explanation, analysis, or additional commentary outside the required
sections.

---

# Writing Priorities

When tradeoffs appear, prefer these outcomes in order:

1. preserve user control
2. preserve reviewed template structure
3. preserve correct existing human-written MR context in update mode
4. prefer reviewer clarity over exhaustiveness
5. prefer bullets over diagrams unless the diagram is clearly better
