import { readFileSync } from "fs"
import { join } from "path"
import { Plugin } from "@opencode/plugin"

// MCP server name (as configured in opencode.json) and the marker ocinit
// prepends to a project's AGENTS.md when it wires codebase-memory in.
const SERVER_NAME = "codebase-memory-mcp"
const GRAPH_MARKER = "<!-- codebase-memory-mcp:start -->"
const AGENTS_FILENAME = "AGENTS.md"

// Injected after a raw search runs. Teaches the class of task rather than
// specific tool names, which differ between direct and Code Mode access.
export const REMINDER =
  "[codebase-memory] Graph is active. Prefer graph discovery for symbols, relationships, " +
  "architecture, callers/callees, and blast-radius analysis; use raw search for exact text " +
  "or graph coverage gaps.\n\n"

// Appended once to raw-search tool descriptions so the model sees the
// guidance before it picks a tool. Keep it short; the graph tools describe
// themselves in detail.
const DESCRIPTION_GUIDANCE =
  "\n\nFor structural symbol, dependency, caller/callee, architecture, or blast-radius " +
  `discovery, prefer ${SERVER_NAME} graph tools when available. Use this tool for exact ` +
  "textual search or when graph coverage is insufficient."

// Substring used to keep the description edit idempotent across replays.
const DESCRIPTION_SENTINEL = `prefer ${SERVER_NAME} graph tools when available`

// How long a negative availability probe is trusted before re-checking. MCP
// servers connect after plugin setup, so the first probe can legitimately miss
// a healthy server.
const AVAILABILITY_TTL_MS = 30_000

// Bound on tracked sessions; cadence counters are per session and worthless
// once a session is long gone.
const MAX_TRACKED_SESSIONS = 500

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

// Emit the reminder on the first 2 detected searches, then on a doubling
// backoff (4, 8, 16, ...). Front-loaded enough to steer, quiet enough to stop
// nagging an agent that keeps choosing raw search deliberately.
export function shouldNudge(count: number): boolean {
  return count <= 2 || (count & (count - 1)) === 0
}

export default Plugin.define({
  id: "codebase-memory-reminder",
  async setup(ctx) {
    // Only arm in projects that opted in to codebase-memory (ocinit writes the
    // marker); a globally configured MCP server must not steer every project.
    if (!projectUsesGraph(ctx.location)) return

    // Pre-selection steering: the model reads these descriptions when choosing
    // a tool, so this is the earliest non-blocking influence available.
    await ctx.tool.transform((editor) => {
      for (const id of ["grep", "glob", "shell"]) {
        editor.update(id, (tool) => {
          if (!tool.description.includes(DESCRIPTION_SENTINEL)) {
            tool.description += DESCRIPTION_GUIDANCE
          }
        })
      }
    })

    // The built-in shell tool regenerates its description on every model
    // request from the detected shell, overwriting transforms. Re-append
    // there; the sentinel keeps this idempotent and grep/glob covered.
    await ctx.session.hook("context", (event) => {
      for (const id of ["grep", "glob", "shell"]) {
        const tool = event.tools[id]
        if (tool && !tool.description.includes(DESCRIPTION_SENTINEL)) {
          tool.description += DESCRIPTION_GUIDANCE
        }
      }
    })

    // Per-session count of detected raw searches.
    const searchCounts = new Map<string, number>()

    // Cached result of the live availability probe.
    let probe: { available: boolean; checkedAt: number } | undefined

    const graphAvailable = async (): Promise<boolean> => {
      const now = Date.now()
      if (probe && (probe.available || now - probe.checkedAt < AVAILABILITY_TTL_MS)) {
        return probe.available
      }
      probe = { available: await probeGraph(ctx), checkedAt: now }
      return probe.available
    }

    // There is no pre-execution nudge: by the time execute.before runs the
    // model has already committed to the call, and V2 offers no channel to
    // change that decision without blocking the tool, which is out of scope.
    await ctx.tool.hook("execute.after", async (event) => {
      try {
        // A failed search is not worth steering; the model is fixing an error.
        if (event.status !== "completed") return
        if (!isRawSearch(event.tool, event.input)) return
        if (!(await graphAvailable())) return

        if (searchCounts.size > MAX_TRACKED_SESSIONS) searchCounts.clear()
        const count = (searchCounts.get(event.sessionID) ?? 0) + 1
        searchCounts.set(event.sessionID, count)
        if (!shouldNudge(count)) return

        event.result = { ...event.result, content: prependReminder(event.result.content) }
      } catch {
        // Reminders must never interfere with tool execution.
      }
    })
  },
})

// Whether the project opted in: the AGENTS.md marker at the session location
// or the canonical checkout. Read once at setup; a new marker needs a reload.
function projectUsesGraph(location: Plugin.Context["location"]): boolean {
  const roots = new Set([location.directory, location.project.canonical])
  for (const root of roots) {
    try {
      if (readFileSync(join(root, AGENTS_FILENAME), "utf8").includes(GRAPH_MARKER)) {
        return true
      }
    } catch {
      // No AGENTS.md at this root.
    }
  }
  return false
}

// Live signal preferred over PATH sniffing: the MCP server may be configured
// as a remote, and a connected server is what actually makes the graph usable.
async function probeGraph(ctx: Plugin.Context): Promise<boolean> {
  try {
    const servers = await ctx.mcp.list()
    if (servers.data.some((s) => s.name === SERVER_NAME && s.status.status === "connected")) {
      return true
    }
  } catch {
    // Fall through to the tool registry probe.
  }
  try {
    const tools = await ctx.tool.list()
    return tools.some((t) => t.id.startsWith(`${SERVER_NAME}_`))
  } catch {
    return false
  }
}

// Raw-search tools the graph can substitute for. `bash` is kept alongside the
// V2 `shell` name for robustness.
export function isRawSearch(tool: string, input: unknown): boolean {
  const name = tool.toLowerCase()
  if (name === "grep" || name === "glob") return true
  if (name !== "shell" && name !== "bash") return false

  const command = (input as { command?: unknown } | undefined)?.command
  return typeof command === "string" && command.length > 0 && isShellSearchCommand(command)
}

type ContentChunk =
  | { type: "text"; text: string }
  | { type: "file"; uri: string; mime: string; name?: string }

// Prepend the reminder to the first text chunk, preserving the rest of the
// result untouched.
export function prependReminder(
  content: string | ReadonlyArray<ContentChunk> | undefined,
): string | ReadonlyArray<ContentChunk> {
  if (content === undefined) return REMINDER
  if (typeof content === "string") return REMINDER + content

  let inserted = false
  const next = content.map((chunk) => {
    if (!inserted && chunk.type === "text") {
      inserted = true
      return { ...chunk, text: REMINDER + chunk.text }
    }
    return chunk
  })
  // Results without a text chunk (for example image-only output) still get the
  // reminder as a leading chunk.
  return inserted ? next : [{ type: "text", text: REMINDER }, ...next]
}

export function isShellSearchCommand(command: string): boolean {
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
