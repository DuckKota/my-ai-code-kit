# My AI Code Kit — Command Cheatsheet

I don't describe what I want in words and hope the agent figures it out. I drive it with slash commands in a fixed order. This file is that flow, the one I actually run.

> [!note]
> The commands in the flows below work the same in any harness. `/advisor` and `/btw` are Oh My Pi built-ins: not part of these workflows, but worth knowing if you use OMP. See [Not part of the flows](#not-part-of-the-flows) below.

---

## Feature flow

For new features, design-reviewable changes, and refactors, one idea walks through sharpen → spec → plan-review → implement → review → close.

| Stage | Command | What it does |
| --- | --- | --- |
| 1. Sharpen | `/grill-me` | Stress-test the idea before you commit to it. |
| 2. Spec | `/opsx-propose` | OpenSpec: turn the idea into a change with design, specs, and a task list. |
| 3. Plan review | `/plannotator-annotate` | Open the Plannotator annotation UI over the OpenSpec plan markdown so a human reviews the spec before implementation. |
| 4. Implement | `/opsx-apply` | Implement the tasks from the OpenSpec change. |
| 4b. Fix loop | `/fix` | When a regression or bug surfaces mid-implementation, diagnose and fix it, then continue. Loop back into `opsx-apply`. |
| 5. Laziness review | `/ponytail-review` | Cut over-engineering in the diff. Run it first so the correctness pass has less to look at. |
| 5b. Correctness review | `/ocr-review` | Open Code Review: correctness over the trimmed diff. Run it second, on what survived ponytail. |
| 6. Close | `/opsx-archive` | Archive the completed OpenSpec change. |
| 6b. Commit | `/commit-message` | Generate a Conventional Commit message from the staged changes. |

---

## Bug-fix contract

**This is the contract. Follow it.** Bug fixes skip the feature ceremony. A bug fix is already scoped; the fix *is* the spec. Don't open an OpenSpec proposal, annotate plans, or archive for a two-line patch.

**Escalation rule:** a bug is worth the full feature flow only when it is architectural: it spans subsystems, needs design decisions, or is really a refactor wearing a bug's clothes. Don't patch it through `/fix`. If you've already diagnosed it, enter the feature flow at the Spec step (`/opsx-propose`). If you haven't, run `/opsx-explore` to design the fix, then `/opsx-propose`. Either way, from Spec onward it's the normal feature flow: apply → review → close.

| Stage | Command | What it does |
| --- | --- | --- |
| 1. Fix | `/fix` | Diagnose and fix the bug or regression at the root cause. |
| 2. Laziness | `/ponytail-review` | Cut over-engineering from the fix. |
| 3. Correctness | `/ocr-review` | Verify the fix is correct. |
| 4. Commit | `/commit-message` | Conventional commit. |

---

## Not part of the flows

`/advisor` and `/btw` are Oh My Pi built-ins, not steps in either flow above.

The `/advisor` is a separate model that reviews the main agent's work as the session unfolds. It can flag a missed requirement, a risky API, weak verification, or unnecessary complexity while the main agent still has a chance to correct course. Use one for long or high-stakes changes, unfamiliar repositories, security-sensitive work, or whenever independent review is worth more than maximum speed.

`/btw` asks an ephemeral side question using the current session context. The exchange isn't added to the persisted conversation, so it takes up no context.
