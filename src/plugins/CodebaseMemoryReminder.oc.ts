import { readFileSync } from "fs"
import { join } from "path"
import type { Plugin } from "@opencode-ai/plugin"

const GRAPH_MARKER = "<!-- codebase-memory-mcp:start -->"
const AGENTS_FILENAME = "AGENTS.md"

const REMINDER = `[codebase-memory] Graph is active — search_graph()/trace_path() may be faster here. Continuing with raw search.

`

// Content-searching binaries on a shell line. Leading-token only.
const SEARCH_BINARIES = new Set([
  "grep",
  "egrep",
  "fgrep",
  "rg",
  "ag",
  "ack",
  "find",
  "fd",
])

// Shell reserved words tolerated before the actual command.
const PRESET_WORDS = new Set(["command", "builtin", "exec", "time", "env", "sudo"])

// Shell control chars and escapes that can precede the first command word.
const LEADING_SEPARATOR_RE = /^[;&|()\s!\\]+/

// Emit the reminder on the first 2 detected searches, then every 10th
// (2, 12, 22, ...) per session.
function shouldNudge(count: number): boolean {
  return count <= 2 || count % 10 === 2
}

export const CodebaseMemoryReminderPlugin: Plugin = async ({ directory, $ }) => {
  // Only arm the reminder when the knowledge graph is actually configured.
  // Binary present...
  try {
    await $`which codebase-memory-mcp`.quiet()
  } catch {
    console.warn("[codebase-memory] binary not in PATH — plugin disabled")
    return {}
  }

  // ...and declared for this project.
  const workspaceRoot = directory || process.cwd()
  const agentsPath = join(workspaceRoot, AGENTS_FILENAME)
  let graphActive = false
  try {
    graphActive = readFileSync(agentsPath, "utf8").includes(GRAPH_MARKER)
  } catch {
    // No AGENTS.md in the workspace.
  }

  if (!graphActive) {
    console.warn("[codebase-memory] AGENTS.md lacks the codebase-memory-mcp marker — plugin disabled")
    return {}
  }

  // Per-session count of detected searches.
  const searchCounts = new Map<string, number>()

  const maybeNudge = (sessionID: string, output: { output: string }) => {
    const count = (searchCounts.get(sessionID) ?? 0) + 1
    searchCounts.set(sessionID, count)
    if (shouldNudge(count)) {
      output.output = REMINDER + output.output
    }
  }

  return {
    "tool.execute.after": async (input, output) => {
      const tool = String(input?.tool ?? "").toLowerCase()

      if (tool === "grep" || tool === "glob") {
        maybeNudge(input.sessionID, output)
        return
      }

      if (tool !== "bash" && tool !== "shell") return

      const command = (input?.args as Record<string, unknown>)?.command
      if (typeof command !== "string" || command.length === 0) return
      if (!isShellSearchCommand(command)) return

      maybeNudge(input.sessionID, output)
    },
  }
}

function isShellSearchCommand(command: string): boolean {
  // Inspect each command segment split on operators, so chained forms like
  // `cd /tmp && rg foo` are caught too. Matching a leading token (not a
  // substring) avoids false positives such as `cp foo.rg bar`.
  return command
    .split(/\n|\|\||&&|[;|]/)
    .map(s => s.trim())
    .filter(s => s.length > 0)
    .some(segIsSearch)
}

function segIsSearch(segment: string): boolean {
  const { first, second } = firstToken(segment)
  if (!first) return false

  // git grep counts as search; git subcommands otherwise are not.
  if (first === "git") return second === "grep"

  return SEARCH_BINARIES.has(first)
}

function firstToken(s: string): { first: string; second: string } {
  let t = s
  for (let i = 0; i < 4; i++) {
    const prev = t
    t = LEADING_SEPARATOR_RE.test(t) ? t.replace(LEADING_SEPARATOR_RE, "") : t
    if (t === prev) break
  }

  // Walk leading non-command tokens: reserved words, env (VAR=value),
  // and flags (with one optional value token) — but never swallow a token
  // that is itself a search binary, so `sudo -E rg` still resolves to rg.
  const toks = t.split(/\s+/).filter(x => x.length > 0)
  let i = 0
  while (i < toks.length) {
    const tok = toks[i].toLowerCase()
    if (PRESET_WORDS.has(tok)) {
      i++
      if (tok === "command" && /^(-v|-V|--)$/.test(toks[i] ?? "")) i += 2
      continue
    }
    if (/^[a-z_][a-z0-9_]*=/i.test(tok)) {
      i++
      continue
    }
    if (/^--/.test(tok)) {
      i++
      continue
    }
    if (/^-/.test(tok)) {
      i++
      if (toks[i] && !/^-/.test(toks[i]) && !SEARCH_BINARIES.has(toks[i])) i++
      continue
    }
    break
  }

  return { first: toks[i]?.toLowerCase() ?? "", second: toks[i + 1]?.toLowerCase() ?? "" }
}