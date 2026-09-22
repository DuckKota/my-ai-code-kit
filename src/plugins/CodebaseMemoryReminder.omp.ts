import fs from "fs"
import path from "path"
import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks"

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
// (2, 12, 22, ...).
function shouldNudge(count: number): boolean {
  return count <= 2 || count % 10 === 2
}

// Whether the codebase-memory-mcp binary is resolvable from PATH. Done with fs
// at load time: OMP extensions load before the runtime is initialized, so
// pi.exec/`$`-style helpers are not available yet.
function binaryOnPath(): boolean {
  const name = "codebase-memory-mcp"
  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    if (!dir) continue
    try {
      fs.accessSync(path.join(dir, name), fs.constants.X_OK)
      return true
    } catch {
      // keep scanning
    }
  }
  return false
}

// OMP extension format: a default-exported factory that binds events with
// pi.on(...). The post-execution `tool_result` event is OMP's analogue of
// opencode's `tool.execute.after`; returning { content } replaces tool output.
export default function codebaseMemoryReminder(pi: HookAPI): void {
  if (!binaryOnPath()) {
    console.warn("[codebase-memory] binary not in PATH — extension disabled")
    return
  }

  // Per-process counter. OMP loads extensions once per session process, so a
  // module-level count is a per-session count; no sessionId is exposed on the
  // tool_result event.
  let searchCount = 0

  pi.on("tool_result", async (event, ctx) => {
    if (event.isError) return

    const tool = String(event.toolName ?? "").toLowerCase()
    if (!isSearchTool(tool, event.input)) return

    const workspaceRoot = ctx?.cwd || process.cwd()
    if (!graphActive(workspaceRoot)) return

    searchCount += 1
    if (!shouldNudge(searchCount)) return

    return { content: prependReminder(event.content) }
  })
}

function isSearchTool(tool: string, input: unknown): boolean {
  if (tool === "grep" || tool === "glob") return true
  if (tool !== "bash" && tool !== "shell") return false

  const command = (input as Record<string, unknown> | undefined)?.command
  if (typeof command !== "string" || command.length === 0) return false
  return isShellSearchCommand(command)
}

// Workspace root -> marker presence, memoized so searches don't re-read
// AGENTS.md on every tool_result event.
const graphCache = new Map<string, boolean>()

function graphActive(workspaceRoot: string): boolean {
  const cached = graphCache.get(workspaceRoot)
  if (cached !== undefined) return cached
  let active = false
  try {
    active = fs.readFileSync(path.join(workspaceRoot, AGENTS_FILENAME), "utf8").includes(GRAPH_MARKER)
  } catch {
    // No AGENTS.md in the workspace.
    active = false
  }
  graphCache.set(workspaceRoot, active)
  return active
}

// Prepend the reminder to the first text chunk of the tool result, keeping the
// original chunks in place. OMP content is a chunk array ({type, text, ...});
// a plain string is wrapped rather than discarded.
function prependReminder(content: unknown): unknown[] {
  if (typeof content === "string") {
    return [{ type: "text", text: REMINDER + content }]
  }
  const chunks = Array.isArray(content) ? content : []
  for (const chunk of chunks) {
    if (chunk && typeof chunk === "object" && (chunk as { type?: string }).type === "text") {
      const text = ((chunk as { text?: string }).text ?? "").toString()
      return chunks.map((c) =>
        c === chunk
          ? { ...(chunk as Record<string, unknown>), text: REMINDER + text }
          : c
      )
    }
  }
  return [{ type: "text", text: REMINDER }, ...chunks]
}

function isShellSearchCommand(command: string): boolean {
  // Inspect each command segment split on operators, so chained forms like
  // `cd /tmp && rg foo` are caught too. Matching a leading token (not a
  // substring) avoids false positives such as `cp foo.rg bar`.
  return command
    .split(/\n|\|\||&&|[;|]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
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
  const toks = t.split(/\s+/).filter((x) => x.length > 0)
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
