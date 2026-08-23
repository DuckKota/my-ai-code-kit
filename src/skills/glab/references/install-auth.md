# glab Install and Auth

Use this reference when `glab` is missing, authentication fails, or the task targets a self-hosted GitLab instance.

## Install `glab`

Verify whether `glab` already exists:

```bash
glab --version
```

Common install branches:

- macOS with Homebrew:
  ```bash
  brew install glab
  ```
- Windows with `winget`:
  ```powershell
  winget install --id GitLab.glab -e
  ```
- Windows with Chocolatey:
  ```powershell
  choco install glab
  ```
- Debian or Ubuntu when package available:
  ```bash
  sudo apt install glab
  ```
- Fedora:
  ```bash
  sudo dnf install glab
  ```

If package path is unclear, use GitLab CLI release instructions: `https://gitlab.com/gitlab-org/cli/-/releases`.

If install succeeds but shell still cannot find `glab`, inspect the executable path and update `PATH` for the current shell profile.

## Authenticate

Interactive login:

```bash
glab auth login
```

Check current auth state:

```bash
glab auth status
```

Token-based login:

```bash
echo "$GITLAB_TOKEN" | glab auth login --stdin
```

Self-hosted login:

```bash
glab auth login --hostname gitlab.example.org
```

## Environment Variables

Use environment variables when interactive login is not right for the task:

```bash
export GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
export GITLAB_HOST=gitlab.example.org
```

## Auth Failure Checks

- `401 Unauthorized`: re-run `glab auth status`, then login again or replace expired token
- `403 Forbidden`: check token scopes and project permissions
- wrong instance or self-hosted mix-up: confirm hostname used during login matches repository target
- multiple accounts: run `glab auth status` and verify the active host before changing credentials

Useful token scopes often include `api`, `read_api`, `read_user`, `read_repository`, and `write_repository`.
