# glab Workflow Patterns

Use this reference after preflight passes and the task needs a common GitLab CLI workflow pattern.

## Repository Targeting

Outside a repository, or when current Git remote is wrong, target explicitly:

```bash
glab mr list -R owner/repo
glab issue list -R owner/repo
```

For self-hosted GitLab, set host first or use a host-qualified target.

## Merge Requests

Create a merge request from current branch:

```bash
git push -u origin feature-branch
glab mr create --title "Add feature" --description "Implements X"
```

Review a merge request locally:

```bash
glab mr list --reviewer=@me
glab mr checkout <mr-number>
glab mr note <mr-number> -m "Please update tests"
glab mr approve <mr-number>
```

If branch already has an MR, inspect that MR before creating another one.

## Issues

Common issue flow:

```bash
glab issue create --title "Bug in login" --label=bug
glab issue list --assignee=@me
glab issue view <issue-number>
```

Link MR to issue in MR description with `Closes #<issue-number>`.

## CI/CD

Inspect and recover pipeline state:

```bash
glab pipeline ci view
glab ci status
glab ci trace
glab ci retry
glab ci lint
```

Use `glab ci lint` before pushing CI config changes.

## API and Automation

Use JSON output before parsing command results:

```bash
glab mr list --output=json
```

Use `glab api` when CLI subcommands do not expose needed behavior:

```bash
glab api projects/:id/merge_requests
glab api --paginate "projects/:id/jobs?per_page=100"
glab api --method POST projects/:id/issues --field title="Bug"
```

Remember: pagination parameters such as `per_page` belong in request URL.
