---
name: grill-me
description: Turn a rough idea into a clear, agent-ready prompt through iterative questioning.
---

Turn the user's brain dump into a prompt for a fresh coding agent.

## Process

### 1. Clarify

Run a `/grilling` session using the user's brain dump as the starting point.

Grill until the user's intent, desired outcome, important requirements, constraints, and material decisions are sufficiently clear to hand to another agent.

Preserve genuine uncertainty. Do not invent decisions.

**Done when:** another agent could understand what the user wants to accomplish and which important decisions remain open.

### 2. Write

Invoke the `writing-for-agents` skill to turn the clarified conversation into the final handoff prompt.

The prompt must preserve the information that another agent needs to make good decisions while removing conversational history, redundant explanation, and information the agent can discover from the repository.

Distinguish user decisions from suggestions and rejected approaches.

### 3. Handoff

The resulting prompt is for a fresh coding agent with no access to this conversation.

Tell that agent to:

1. Understand the requested outcome.
2. Inspect the repository and relevant existing implementation.
3. Validate the request against the actual codebase.
4. Create an OpenSpec proposal.
5. Stop for the user's review and approval before implementation.

The prompt should leave implementation decisions discoverable through repository investigation when they have not already been settled.

## Output

Return only the finished prompt for the fresh agent.

The prompt is complete when it contains everything the fresh agent needs from this conversation to produce a well-informed OpenSpec proposal without having access to the original conversation.
