# My AI Code Kit

### Install

```bash
git clone https://github.com/DuckKota/my-ai-code-kit.git
cd my-ai-code-kit
./bin/setup install   # requires python 3.9+

# Inside a git repository, `setup install` also installs and initializes OpenSpec and codebase-memory-mcp for that project (prompts first; idempotent).
```

<details>
  <summary>Install Ponytail</summary>

  **Oh My Pi:** Run the command `omp install git:github.com/DietrichGebert/ponytail`

  **OpenCode:** Add the plugin `"plugin": ["@dietrichgebert/ponytail"]` to your `opencode.json` file
</details>

<details>
  <summary>Magic Context</summary>

  Run the command `curl -fsSL https://raw.githubusercontent.com/cortexkit/magic-context/master/scripts/install.sh | bash`
</details>

### The Complete Kit

> [!NOTE]
> My workflow is designed with a "command first" approach. My personal OMP command reference lives in [CHEATSHEET.md](./CHEATSHEET.md).

**Commands:** [/commit-message](./src/commands/commit-message.md) • [/grill-me](./src/commands/grill-me.md) • [/fix](./src/commands/fix.md) • [/handoff](./src/commands/handoff.md) • [/glab-mr](./src/commands/glab-mr.md) • [/ponytail](https://ponytail.dev/) • [/ponytail-review](https://ponytail.dev/)

**Skills:** [diagnosing-bugs](./src/skills/diagnosing-bugs/) • [codebase-design](./src/skills/codebase-design/) • [domain-modeling](./src/skills/domain-modeling/) • [improve-codebase-architecture](./src/skills/improve-codebase-architecture/) • [using-git-worktrees](./src/skills/using-git-worktrees/) • [verification-before-completion](./src/skills/verification-before-completion/)

**Tools:** [codebase-memory-mcp](https://deusdata.github.io/codebase-memory-mcp/) • [OpenSpec](https://openspec.dev/) • [ponytail](https://ponytail.dev/) • [Magic Context](https://github.com/cortexkit/magic-context)

**Other:** [caveman](./src/instructions/caveman.md) • [batch-file-writes](./src/instructions/file-edit-limits.md)


---

<div align="center">
  <img src=".img/oc.png" alt="OpenCode" width="96" height="96"/>&nbsp;&nbsp;&nbsp;
  <img src=".img/omp.png" alt="Oh My Pi" width="96" height="96"/>
</div>

<div align="center">
    Apache 2.0
</div>
