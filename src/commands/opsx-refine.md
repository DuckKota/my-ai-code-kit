---
description: Perform a deliberate second planning pass over an existing OpenSpec change
---

# OpenSpec Refine

Perform a deliberate second planning pass over an existing OpenSpec change to improve its correctness, clarity, simplicity, and implementation readiness.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Optionally specify a change name after `/opsx-refine` (e.g., `/opsx-refine add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Refining change: <name>" and how to override (e.g., `/opsx-refine <other>`).

2. **Check status and resolve context**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context
   - Which artifacts currently exist (proposal, design, specs, tasks)

3. **Read the change as a whole**
   Read all relevant artifacts belonging to the OpenSpec change listed under `artifactPaths` before modifying them. Inspect available:
   - proposal
   - design
   - specifications
   - task list
   - supporting OpenSpec artifacts

   Do not review these files independently. Build a coherent model of:
   - what behavior is changing
   - why the change exists
   - what constraints apply
   - how the proposed design satisfies the requirements
   - how the implementation tasks realize that design
   - how completion will be verified

   Then compare the artifacts against one another to identify gaps, contradictions, or mismatched assumptions.

## Core Principles

### Refine the Existing Proposal

Treat the current OpenSpec change as the intended solution unless evidence shows that part of it is flawed.

Do not redesign the change merely because another approach is possible.

Change something only when there is a concrete reason, such as:
- a contradiction
- an unsupported assumption
- ambiguous behavior
- missing required behavior
- unnecessary complexity
- conflict with an established repository pattern
- incorrect task sequencing
- insufficient verification
- an implementation risk that the current plan does not account for

When the proposal is already sound, preserve it.

Do not make cosmetic edits simply to demonstrate that refinement occurred.

### Verify Instead of Guessing

When evaluating a claim about the existing repository, inspect the repository rather than assuming the proposal is correct.

Relevant questions may include:
- Does the referenced abstraction actually exist?
- Does the repository already solve a similar problem?
- Is the proposed responsibility assigned to the correct component?
- Are callers behaving the way the proposal assumes?
- Does the proposed implementation follow existing conventions?
- Do the suggested verification commands or tests actually exist?

Repository evidence outranks assumptions made during planning.

If something cannot yet be verified without implementation, explicitly identify it as an assumption rather than converting it into a fact.

### Prefer Simplicity

Actively look for over-engineering.

Ask whether the proposed change introduces:
- unnecessary abstractions
- premature generalization
- duplicate concepts
- unnecessary interfaces
- configuration for hypothetical future requirements
- new architectural layers when an existing path can be extended
- unrelated cleanup
- unnecessary migration machinery

Prefer the smallest design that cleanly satisfies the stated requirements and fits the existing codebase.

Do not sacrifice clarity for theoretical flexibility.

### Preserve Scope

Do not expand the requested change.

Do not introduce speculative requirements.

Do not use refinement as an excuse to clean up unrelated code or redesign neighboring systems.

If unrelated problems are discovered, mention them only when they materially affect the proposed change.


### Persist Implementation-Relevant Context

Assume implementation may happen later in a fresh AI context with no access to this refinement conversation or final response.

Any information that is expected to influence implementation must be persisted in the OpenSpec change itself.

Do not rely on conversational context to carry forward:
- implementation watchpoints
- important assumptions
- investigation targets
- verification strategy
- sequencing constraints
- skill recommendations
- other execution guidance that would materially affect how the change is implemented

Place durable guidance in the most appropriate existing OpenSpec artifact.

Prefer updating authoritative artifacts such as the design, specifications, or task list over creating a separate handoff document.

Create a supplementary artifact only when the guidance is important, does not fit naturally in an existing authoritative artifact, and the schema permits it.

The command's final response is only a summary for the current user. It must not contain implementation-critical information that was not also persisted in the OpenSpec change.

## Detailed Review Guidelines

### Refine Requirements and Specifications

Review requirements and scenarios for:
- ambiguity
- missing behavior
- undefined edge cases
- hidden assumptions
- contradictory requirements
- missing failure behavior
- backwards-compatibility concerns
- unverifiable statements
- accidental scope expansion

Specifications should describe observable behavior clearly enough that implementation and verification do not require guessing.

Do not add edge cases simply because they are imaginable. Add them when they are relevant to the requested behavior or represent a realistic failure mode.

### Refine the Design

Review the proposed design for:
- responsibility placed in the wrong component
- duplication of an existing repository abstraction
- unnecessary new abstractions
- hidden coupling
- dependency-direction problems
- unclear state ownership
- lifecycle ambiguity
- migration problems
- compatibility problems
- concurrency assumptions
- error-handling gaps
- architectural decisions unsupported by repository evidence

Prefer extending established repository patterns when they fit the requirement.

If the design is fundamentally wrong, fix the authoritative OpenSpec artifacts rather than attempting to compensate with implementation notes.

### Refine the Task Plan

Review the task list for:
- tasks that are too broad
- meaningless micro-tasks
- unclear completion conditions
- missing implementation steps
- incorrect dependency ordering
- tasks that do not correspond to a requirement or design decision
- verification deferred until too late
- duplicated work
- unrelated cleanup

Tasks should be concrete enough that an implementation agent can act on them without reconstructing the entire design.

Order tasks according to real dependencies.

For example, do not schedule use of a new API before the API exists, or removal of a compatibility path before its callers have migrated.

Add or improve verification steps where they materially improve confidence.

Do not invent commands, tests, or tools that have not been verified to exist in the repository.

### Check Implementation Readiness

After reviewing the proposal itself, determine whether an implementation agent could begin work using only the repository and the refined OpenSpec change, without access to this conversation and without needing to rediscover important planning context.

Look for missing information such as:
- important repository conventions
- existing abstractions that should be reused
- similar implementations worth inspecting
- non-obvious sequencing constraints
- compatibility requirements
- regression-sensitive behavior
- assumptions that should be confirmed during implementation
- meaningful verification targets

Whenever possible, encode durable information in the appropriate authoritative OpenSpec artifact rather than creating redundant notes.

### Plan Skill Usage Deliberately

Inspect the skills available in the current environment as part of every refinement pass.

Do not assume any specific skill exists.

Do not maintain or rely on a hard-coded list of skills.

Use a discovery funnel:

1. Discover the available skill names and descriptions.
2. Shortlist skills that plausibly match the actual implementation work.
3. Inspect the detailed guidance only for plausible matches.
4. Classify each useful skill as intrinsically applicable or conditionally applicable.
5. Record only the skills that are likely to improve implementation quality.

Be exhaustive in discovery, but selective in recommendation.

Do not dump the entire skill catalog into the plan.

Do not recommend skills merely to make the refinement appear thorough.

#### Identify Intrinsically Applicable Skills

Some skills are useful because of the nature of the work itself.

A skill is intrinsically applicable when the planned implementation directly falls within the skill's specialized domain or method and that guidance is likely to materially improve execution.

Examples include:
- a frontend design skill for work whose primary deliverable is a substantial user interface
- a database migration skill for a change that includes schema migration
- an API design skill for a change that creates or materially changes a public API

These are examples of applicability, not a hard-coded skill list.

For an intrinsically applicable skill, the planned work itself is the trigger. Do not require an additional failure condition or unusual implementation event.

Record:
- the skill
- the part of the planned work it directly applies to
- why its specialized guidance is likely to improve implementation

For example:

```text
Skill: <skill-name>

Applies to:
<specific planned work that directly falls within the skill's domain>

Purpose:
<why the skill's guidance is likely to improve that work>
```

#### Identify Conditionally Applicable Skills

Other skills become useful only if a specific condition arises during implementation.

For a conditionally applicable skill, record:
- the skill
- the specific concern it addresses
- the observable condition under which it should be used

For example:

```text
Skill: <skill-name>

Trigger:
Use when implementation reveals <specific observable condition>.

Purpose:
<why this skill is useful under that condition>
```

Good triggers are based on observable implementation conditions.

Bad triggers are vague category labels such as:
```text
Use for architecture work.
```

Better:
```text
Use if implementation requires introducing a new abstraction,
moving responsibility between components, or creating a dependency
relationship that does not already exist.
```

#### Persist Skill Guidance for Implementation

Any skill identified as useful must be recorded in an OpenSpec artifact that the implementation agent is expected to read.

Do not leave skill guidance only in the refinement summary.

Place skill guidance where it best fits:
- task-specific skill guidance should normally live with the relevant implementation task
- cross-cutting skill guidance should normally live in the design or another appropriate implementation-guidance section
- avoid creating a dedicated skill artifact unless there is a concrete reason the existing artifacts cannot represent the guidance clearly

For intrinsically applicable skills, record what planned work the skill applies to and why it is useful.

For conditionally applicable skills, record the observable trigger and purpose.

The implementation agent should be able to discover the intended skill usage from the OpenSpec change alone.

#### Skill Planning Is Guidance, Not a Mandate

Do not require implementation to use a skill simply because it was identified during refinement.

Implementation may reveal information that was unavailable during planning.

A skill judged intrinsically applicable may turn out not to be useful once the real implementation path is understood.

A conditional skill may become useful even if its trigger was not anticipated exactly.

Implementation may also discover a useful skill that refinement did not predict.

Later repository and implementation evidence should always override earlier planning predictions.

### Create Supplementary Implementation Guidance Only When Useful

Most refinement should happen directly in the authoritative OpenSpec artifacts.

If useful implementation guidance remains that does not belong naturally in the proposal, design, specs, or tasks, record it concisely in an appropriate OpenSpec artifact.

Any such guidance that is expected to affect implementation must be persisted before refinement is considered complete.

Do not create supplementary documentation merely because this command was invoked.

Useful guidance may include:

#### Investigation Targets

A small number of repository areas worth inspecting before or during implementation, such as:
- an existing implementation of similar behavior
- the abstraction being extended
- relevant registration or composition code
- regression-sensitive tests
- configuration boundaries

Keep this focused. Do not produce a repository tour.

#### Risks and Watchpoints

Record concrete implementation risks.

Good:
```text
The existing parser ignores unknown fields. Adding the new field
must not accidentally make parsing strict.
```

Bad:
```text
Be careful about regressions.
```

A useful watchpoint tells the implementation agent exactly what behavior or assumption deserves attention.

#### Verification Strategy

Identify evidence that would meaningfully demonstrate correctness.

Prefer, where appropriate:
1. existing focused automated tests
2. new focused automated tests
3. integration or end-to-end tests
4. targeted runtime verification
5. static inspection when behavior cannot reasonably be executed

Do not merely say "run the tests." Identify the relevant behavior or test area when it can be determined from the repository.

## Do Not Overproduce

This refinement pass should be high-signal.

Do not:
- restate the proposal
- paraphrase requirements into another document
- create artifacts with no new information
- assign a skill to every task
- generate speculative implementation instructions
- convert every observation into a new task
- rewrite correct text for stylistic reasons
- invent future requirements
- perform production implementation
- perform unrelated cleanup

A successful refinement may result in only a few changes.

A successful refinement may also conclude that the existing proposal is already strong.

## Handle Uncertainty Explicitly

When an important assumption can be checked now, check it.

When it cannot yet be resolved, record it clearly.

For example:
```text
Assumption to confirm during implementation:
The design assumes callers normalize identifiers before invoking
this service. Confirm this before relying on that behavior.
```

Do not hide uncertainty behind confident wording.

## Completion Criteria

The refinement is complete when:
- the OpenSpec artifacts form one coherent plan
- requirements and design agree
- specifications describe the important observable behavior
- material assumptions are verified or explicitly identified
- obvious over-engineering has been removed
- the design fits established repository patterns where appropriate
- tasks are clear, sensibly scoped, and correctly ordered
- meaningful verification is represented
- important implementation risks are captured
- all implementation-relevant refinement guidance has been persisted in the OpenSpec change
- the change is understandable and actionable from a fresh implementation context without relying on this conversation
- available skills have been deliberately inspected
- intrinsically applicable skills have been identified where the planned work directly benefits from them
- conditionally applicable skills have clear observable triggers where appropriate
- no skills have been recommended merely because they are available
- no unnecessary artifacts or planning material have been created
- no meaningful refinement remains

Stop when these conditions are satisfied. Do not continue polishing for its own sake.

## Output Templates

**Output On Success (Defects Found & Fixed)**

```
## Refinement Complete: <change-name>

**Schema:** <schema-name>
**Status:** Refined with structural improvements

### Material Changes Made
- Updated <artifact> to resolve <issue/contradiction>
- Removed over-engineering from <design aspect>
- Adjusted task sequencing for dependency safety
- Persisted implementation-relevant guidance in <artifact>

### Important Assumptions, Risks, or Gaps Discovered
- <Discovered gaps or risks>

### Implementation Guidance & Watchpoints
- <Investigation targets, watchpoints, or verification strategy>

### Skills Identified

**Intrinsically Applicable**
- **<skill-name>**: Applies to <specific planned work>. Purpose: <why its guidance should improve implementation>.

**Conditionally Applicable**
- **<skill-name>**: Triggered if <observable condition>. Purpose: <why it helps>.

The change plan is now robust and ready for implementation via `/opsx-apply`.
```

**Output On Success (Already Clean)**

```
## Refinement Complete: <change-name>

**Schema:** <schema-name>
**Status:** Verified clean (no material changes needed)

The existing proposal, design, specs, and tasks are coherent, simple, and well-sequenced. No structural defects or over-engineering were found.

Ready for implementation via `/opsx-apply`.
```

**Guardrails**
- **Do NOT implement anything.** You are reviewing and refining documentation/artifacts only.
- **Do NOT overproduce.** If the proposal is already sound, preserve it. Do not make edits just to show activity.
- **Do NOT orchestrate.** Keep this command self-contained; do not inject workflow history or assumptions about preceding/succeeding commands.
- **Do NOT rely on chat continuity.** Assume implementation may occur in a fresh context. Persist any implementation-relevant guidance in the OpenSpec change itself.
- **Do not maintain hard-coded skill lists.** Discover the current skill catalog dynamically, shortlist by relevance, and distinguish intrinsic applicability from conditional applicability.
- **Handle uncertainty explicitly.** If an assumption cannot be checked yet, record it clearly rather than guessing.