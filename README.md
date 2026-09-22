# My AI Code Kit

### Install

```bash
git clone https://github.com/DuckKota/my-ai-code-kit.git
cd my-ai-code-kit
./bin/setup install   # requires python 3.9+

# Inside a git repository, `setup install` also installs and initializes
# OpenSpec and codebase-memory-mcp for that project (prompts first; idempotent).
```

> [!important]
> Manually install the following:
>
> - [Ponytail](https://github.com/DietrichGebert/ponytail#readme)
> - [Planotator](https://plannotator.ai/)
> - [Magic Context](https://github.com/cortexkit/magic-context)
> - [Open Code Review](https://github.com/alibaba/open-code-review/blob/main/plugins/open-code-review/opencode/README.md)

### The Complete Kit

> [!tip]
> My workflow is designed with a **command-first** approach. See my [CHEATSHEET.md](./CHEATSHEET.md) to see how I work.

<details>
<summary>The full kit...</summary>

> **Commands**
> 
> - [`/commit-message`](./src/commands/commit-message.md)
> - [`/grill-me`](./src/commands/grill-me.md)
> - [`/fix`](./src/commands/fix.md)
> - [`/handoff`](./src/commands/handoff.md)
> - [`/humanizer`](./src/commands/humanizer.md)
> - [`/ponytail`](https://ponytail.dev/)
> - [`/ponytail-review`](https://ponytail.dev/)

> **Skills**
> 
> - [`diagnosing-bugs`](./src/skills/diagnosing-bugs/)
> - [`codebase-design`](./src/skills/codebase-design/)
> - [`domain-modeling`](./src/skills/domain-modeling/)
> - [`humanize-writing`](./src/skills/humanize-writing/)
> - [`improve-codebase-architecture`](./src/skills/improve-codebase-architecture/)
> - [`using-git-worktrees`](./src/skills/using-git-worktrees/)
> - [`verification-before-completion`](./src/skills/verification-before-completion/)

> **Tools**
> 
> - [`codebase-memory-mcp`](https://deusdata.github.io/codebase-memory-mcp/)
> - [`OpenSpec`](https://openspec.dev/)

> **Others**
> 
> - [`caveman`](./src/instructions/caveman.md)
> - [`batch-file-writes`](./src/instructions/file-edit-limits.md)

</details>

---

<div align="center">
  <img src=".img/oc.png" alt="OpenCode" width="96" height="96"/>&nbsp;&nbsp;&nbsp;
  <img src=".img/omp.png" alt="Oh My Pi" width="96" height="96"/>
</div>

<div align="center">
    Apache 2.0
</div>
