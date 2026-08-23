# glab Troubleshooting

Use this reference for recurring failures after install and auth basics are already known.

## First Checks

Run these before deeper troubleshooting:

```bash
glab --version
glab auth status
git remote -v
glab <command> --help
```

## Missing Command

Error examples:

```text
command not found: glab
glab: command not found
```

Action:
- Load `references/install-auth.md`
- Verify `glab` is installed and on `PATH`

## Auth and Permission Failures

### `401 Unauthorized`

Likely causes:
- not logged in
- expired token
- wrong GitLab host

Action:
- run `glab auth status`
- login again with `glab auth login`
- confirm self-hosted hostname if not using `gitlab.com`

### `403 Forbidden` or `insufficient permissions`

Likely causes:
- token missing needed scopes
- user lacks project access

Action:
- check token scopes such as `api`, `read_api`, `read_user`, `read_repository`, and `write_repository`
- confirm project membership and role

### Multiple Accounts or Wrong Host

Action:
- run `glab auth status`
- confirm active account and host
- for self-hosted targets, use `GITLAB_HOST` or a host-qualified `-R` target

## Repository Targeting Failures

### `not a git repository`

Action:
- run command from repository root, or
- target repository explicitly:
  ```bash
  glab mr list -R owner/repo
  ```

### `404 Project Not Found`

Likely causes:
- wrong `owner/repo`
- wrong GitLab host
- no access to project

Action:
- inspect `git remote -v`
- verify repository path in GitLab
- use explicit `-R owner/repo`
- confirm host with `glab auth status`

### Wrong Repository Auto-Detected

Action:
- inspect `git remote -v`
- rerun command with explicit `-R owner/repo`

## Merge Request Failures

### `source branch already has a merge request`

Action:

```bash
glab mr list
glab mr list --source-branch=$(git branch --show-current)
glab mr view <mr-number>
```

Update existing MR instead of creating another one.

### Merge Conflicts

Action:

```bash
glab mr checkout <mr-number>
git fetch origin main
git merge origin/main
```

If team prefers rebase, use `git rebase origin/main` instead.

### Pipeline Must Succeed

Action:

```bash
glab ci status
glab pipeline ci view
glab ci retry
```

## CI/CD Failures

### `pipeline not found`

Likely causes:
- no pipeline exists yet
- wrong branch or project target

Action:

```bash
glab ci run
glab ci status --branch=main
```

### `.gitlab-ci.yml is invalid`

Action:

```bash
glab ci lint
```

Common causes:
- YAML indentation mistakes
- invalid job names
- missing required fields

### Artifact Download Failures

Action:

```bash
glab ci view <pipeline-id>
glab ci retry
```

Confirm job actually produced artifacts and they have not expired.

## Network and Certificate Failures

### `dial tcp: i/o timeout`

Action:
- verify network path to GitLab instance
- confirm GitLab service status
- check firewall or proxy interference

### `x509: certificate signed by unknown authority`

Action:
- prefer adding certificate to trust store or configuring Git CA bundle
- avoid disabling SSL verification except short-lived local testing

## Output and Config Failures

### Garbled Output

Action:

```bash
export GLAMOUR_STYLE=notty
glab mr list --output=text
```

### JSON Parsing Problems

Action:

```bash
glab mr list --output=json | jq '.'
```

Confirm command supports JSON and stderr is not mixed into stdout.

### Broken Config

Error example:

```text
failed to load config
```

Action:
- inspect `~/.config/glab-cli/config.yml`
- back up corrupted config before re-running `glab auth login`

## Escalation

If branch still fails:
- check `https://status.gitlab.com`
- consult `https://docs.gitlab.com/editor_extensions/gitlab_cli/`
- search `https://gitlab.com/gitlab-org/cli/-/issues`
- capture `glab --version`, exact error text, target host, and command used
