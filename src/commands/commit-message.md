---
description: Generate Conventional Commit Message
---

# Task

Generate a Conventional Commit message from the staged Git changes.

You must:

1. Analyze only staged changes.
2. Generate exactly one Conventional Commit message.
3. Validate the generated commit message using the repository's commit validation script.
4. Provide the exact `git commit` command for the user.

---

# Execution Workflow

Follow these steps in order.

## Step 1: Verify staged changes

Run:

```bash
git diff --cached
```

If no staged changes exist:

STOP.

Tell the user:

- no staged changes were found
- they should stage changes first (example: `git add .`)

Do not continue.

**Done when** `git diff --cached` shows staged changes.

---

## Step 2: Determine issue number

Run:

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

The issue number is mandatory.

If an issue number cannot be found:

STOP.

Ask the user for the issue number.

Use only an issue number found in the branch name or confirmed by the
user, and carry it into the footer.

**Done when** you hold a real issue number from the branch name or the
user.

---

## Step 3: Analyze the change

Determine:

1. Commit type
2. Scope
3. Summary
4. Body
5. Footer

### Commit Type

Choose exactly one:

- build
- chore
- ci
- dep
- docs
- feat
- fix
- perf
- refactor
- revert
- style
- test

Select the type that best represents the primary purpose of the change.

When multiple types appear applicable, choose the type representing the
primary externally observable outcome rather than the implementation
mechanics.

---

### Scope

Include a scope only when the changes belong to one clear, high-level
component.

Rules:

- lowercase
- kebab-case
- omit for global or cross-cutting changes
- name a real component, not a bare directory

---

### Summary

Requirements:

- imperative mood
- present tense
- starts with a lowercase letter
- no trailing period
- describes the primary change
- maximum 72 characters

---

### Body

The body is required.

Focus on explaining:

- why the change exists
- what changed
- notable implementation decisions
- impact on users or developers

Say what the diff does not: the reason, the decisions, and the impact —
not a re-read of the changed lines.

Wrap lines at 72 characters.

When the change bundles two or more independent changes, enumerate each as
its own bullet. A change is independent when splitting it off would leave a
meaningless commit subject: two files of one fix are one change; two fixes
in one file are two. Each bullet is an imperative sentence, lowercase start,
no trailing period, wrapped at 72 characters. The subject still names the
dominant change; the body enumerates the rest.

---

### Footer

The footer is required.

The footer must contain:

```
<GitLab keyword> #<issue>
```

Choose the keyword based on commit type:

- fix → Fixes
- feat → Implements
- all others → Closes

Examples:

```
Fixes #123
```

```
Implements #456
```

```
Closes #789
```

**Done when** type, scope, summary, body, and footer are all decided.

---

## Step 4: Validate the commit message

Validate the generated commit message by executing the commit
validation script located at:

<VALIDATE_COMMIT_SCRIPT>

Pass the complete generated commit message to the script via standard input.

Expected invocation pattern:

printf '%s\n' "<complete commit message>" | <VALIDATE_COMMIT_SCRIPT>

Treat the validator as the source of truth.

If validation succeeds:

Continue.

If validation fails:

- use the validator's error message to determine what must be corrected
- revise the commit message
- run the validator again

Repeat until validation succeeds.

**Done when** the validator accepts the message.

---

## Step 5: Quality Gate

Before responding, validate each component against the rules above:

- Subject ≤ 72 chars, imperative, lowercase start, no period?
- Two or more independent changes → body enumerates them as bullets?
- Body explains *why* not *what* (diff already shows what)?
- Footer keyword matches type (Fixes/Implements/Closes)?
- Issue number present and real?

If any rule is violated: fix it, then re-run validation before continuing.

**Done when** every component passes and validation succeeds.

---

# Output Format

Return only:

## 1. Commit message

Inside a fenced code block:

With scope:

```text
<type>(<scope>): <summary>

<body>

<footer>
```

Without scope:

```text
<type>: <summary>

<body>

<footer>
```

## 2. Git command

Provide the exact command:

```bash
git commit -m "<subject>" -m "<body>" -m "<footer>"
```

Use multiple `-m` flags for shell compatibility.

Do not execute the command.

Return no explanation, analysis, or additional commentary outside the
required commit message and git command.