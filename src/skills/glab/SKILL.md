---
name: glab
description: Decision guide for the GitLab CLI (`glab`): merge requests, issues, CI/CD, direct `glab api` calls, and repository targeting. Use when GitLab work needs the command line, or when `glab` install, auth, or targeting fails.
---

# GitLab CLI (glab) Skill

Use `glab` for GitLab work from terminal. Treat `glab --help` as source of truth for routine syntax and flags.

## Use This Skill When

- Create, review, or manage merge requests
- Work with issues, releases, variables, or repositories through GitLab CLI
- Monitor, trigger, or troubleshoot GitLab CI/CD from terminal
- Use `glab api` for direct GitLab API calls
- Troubleshoot `glab` installation, authentication, repository targeting, or self-hosted access

## Preflight

1. Confirm command exists:
   ```bash
   glab --version
   ```
   If command missing, load `references/install-auth.md`. Do not continue to task commands until install path is clear.

2. Confirm authentication:
   ```bash
   glab auth status
   ```
   If unauthenticated, token expired, or host wrong, load `references/install-auth.md`.

3. Confirm repository target:
   - Inside repository, check `git remote -v` if target seems wrong.
   - Outside repository, or when auto-detection is unreliable, use `-R owner/repo`.
   - For self-hosted GitLab, set `GITLAB_HOST` or use host-qualified repository targets.

## Command Discovery

- For ordinary command syntax, inspect `glab <area> --help` first.
- Prefer live command help over cached examples.
- Use `--output=json` when user needs scripting or machine-readable output.
- Use `--web` when user wants browser handoff instead of terminal output.

## glab api

- Pagination parameters belong in request URL, not as standalone `glab api` flags.
- Use `--paginate` to fetch successive pages.
- Safe pattern:
  ```bash
  glab api --paginate "projects/:id/jobs?per_page=100"
  ```
- Wrong pattern:
  ```bash
  glab api --per-page=100 projects/:id/jobs
  ```

## Progressive Disclosure

- Load `references/install-auth.md` for install, authentication, token, and self-hosted setup branches.
- Load `references/workflow-patterns.md` for common merge request, issue, pipeline, and API usage patterns after preflight passes.
- Load `references/troubleshooting.md` for recurring failures such as missing command, auth errors, wrong repository, pipeline gating, or certificate problems.

## Quick Recovery Hints

- `command not found: glab`: load install guidance first
- `401 Unauthorized` or `403 Forbidden`: inspect `glab auth status`, token scopes, and host selection
- `404 Project Not Found` or wrong project: verify `git remote -v` and use `-R owner/repo`
- `not a git repository`: run from repository root or provide `-R owner/repo`
- existing MR on source branch: inspect current branch MR before creating another


