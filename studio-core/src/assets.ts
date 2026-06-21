// Integrate the user's existing Claude assets into a factory's agents. Because
// the factory brain/build backends drive the local Claude Code CLI, anything
// configured for that login is reusable: skills auto-resolve from user
// settings, and MCP servers / plugins / subagents / extra context dirs can be
// injected per job via CLI flags. assetArgs() turns a ClaudeAssets bundle into
// those flags; assetsFromEnv() lets a deployment set them once via env.

export interface ClaudeAssets {
  /** MCP server config JSON files → --mcp-config (your existing MCP servers). */
  mcpConfig?: string[]
  /** Extra trusted dirs (CLAUDE.md / project skills / context) → --add-dir. */
  addDirs?: string[]
  /** Plugin dirs/zips → --plugin-dir (your slash-commands/hooks/subagents). */
  pluginDirs?: string[]
  /** Plugin URLs → --plugin-url. */
  pluginUrls?: string[]
  /** Custom subagents JSON → --agents. */
  agentsJson?: string
  /** Settings file → --settings. */
  settings?: string
  /** Extra pre-approved tools → --allowedTools (merged with the backend's). */
  allowedTools?: string[]
  /** Model override → --model. */
  model?: string
  /** Fallback model(s) → --fallback-model. */
  fallbackModel?: string
}

/** Build the Claude Code CLI flags for a set of assets. */
export function assetArgs(a: ClaudeAssets): string[] {
  const out: string[] = []
  if (a.model) out.push('--model', a.model)
  if (a.fallbackModel) out.push('--fallback-model', a.fallbackModel)
  if (a.settings) out.push('--settings', a.settings)
  if (a.agentsJson) out.push('--agents', a.agentsJson)
  for (const f of a.mcpConfig ?? []) out.push('--mcp-config', f)
  for (const d of a.addDirs ?? []) out.push('--add-dir', d)
  for (const p of a.pluginDirs ?? []) out.push('--plugin-dir', p)
  for (const u of a.pluginUrls ?? []) out.push('--plugin-url', u)
  if (a.allowedTools?.length) out.push('--allowedTools', ...a.allowedTools)
  return out
}

const csv = (v?: string): string[] | undefined =>
  v ? v.split(',').map((s) => s.trim()).filter(Boolean) : undefined

/** Read a default asset bundle from env so a deployment configures it once. */
export function assetsFromEnv(env: NodeJS.ProcessEnv = process.env): ClaudeAssets {
  const a: ClaudeAssets = {}
  const mcp = csv(env.STUDIO_MCP_CONFIG)
  const dirs = csv(env.STUDIO_ADD_DIRS)
  const plugins = csv(env.STUDIO_PLUGIN_DIRS)
  const pluginUrls = csv(env.STUDIO_PLUGIN_URLS)
  const tools = csv(env.STUDIO_EXTRA_TOOLS)
  if (mcp) a.mcpConfig = mcp
  if (dirs) a.addDirs = dirs
  if (plugins) a.pluginDirs = plugins
  if (pluginUrls) a.pluginUrls = pluginUrls
  if (tools) a.allowedTools = tools
  if (env.STUDIO_AGENTS_JSON) a.agentsJson = env.STUDIO_AGENTS_JSON
  if (env.STUDIO_CLAUDE_SETTINGS) a.settings = env.STUDIO_CLAUDE_SETTINGS
  if (env.STUDIO_MODEL) a.model = env.STUDIO_MODEL
  if (env.STUDIO_FALLBACK_MODEL) a.fallbackModel = env.STUDIO_FALLBACK_MODEL
  return a
}
