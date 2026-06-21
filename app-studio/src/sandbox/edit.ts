// sandbox::edit — file operations confined to a project's workdir. Mirrors the
// Anthropic text-editor tool commands (view / create / str_replace / insert)
// so the build loop can bridge tool_use blocks straight through.
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { ensureWorkspace, resolveInside } from './workspace.js'

export type EditCommand = 'view' | 'create' | 'str_replace' | 'insert'

export interface EditInput {
  project_id: string
  command: EditCommand
  path: string
  file_text?: string
  old_str?: string
  new_str?: string
  insert_line?: number
  insert_text?: string
  view_range?: [number, number]
}

export interface EditResult {
  ok: boolean
  content?: string
  diff?: string
  error?: string
}

export async function editInWorkspace(input: EditInput): Promise<EditResult> {
  await ensureWorkspace(input.project_id)
  try {
    const abs = await resolveInside(input.project_id, input.path)
    switch (input.command) {
      case 'view':
        return await view(abs, input.view_range)
      case 'create':
        return await create(abs, input.file_text ?? '')
      case 'str_replace':
        return await strReplace(abs, input.old_str ?? '', input.new_str ?? '')
      case 'insert':
        return await insert(abs, input.insert_line ?? 0, input.insert_text ?? '')
      default:
        return { ok: false, error: `unknown command: ${input.command as string}` }
    }
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) }
  }
}

async function view(abs: string, range?: [number, number]): Promise<EditResult> {
  const s = await stat(abs)
  if (s.isDirectory()) {
    const entries = await readdir(abs, { withFileTypes: true })
    const listing = entries
      .map((e) => (e.isDirectory() ? `${e.name}/` : e.name))
      .sort()
      .join('\n')
    return { ok: true, content: listing }
  }
  let text = await readFile(abs, 'utf8')
  if (range) {
    const lines = text.split('\n')
    const [start, end] = range
    text = lines.slice(Math.max(0, start - 1), end === -1 ? undefined : end).join('\n')
  }
  return { ok: true, content: text }
}

async function create(abs: string, fileText: string): Promise<EditResult> {
  await mkdir(path.dirname(abs), { recursive: true })
  await writeFile(abs, fileText, 'utf8')
  return { ok: true, diff: `created ${path.basename(abs)} (${fileText.length} bytes)` }
}

async function strReplace(abs: string, oldStr: string, newStr: string): Promise<EditResult> {
  if (oldStr.length === 0) return { ok: false, error: 'old_str must not be empty' }
  const text = await readFile(abs, 'utf8')
  const count = occurrences(text, oldStr)
  if (count === 0) return { ok: false, error: 'old_str not found' }
  if (count > 1) return { ok: false, error: `old_str matched ${count} times; must be unique` }
  const next = text.replace(oldStr, newStr)
  await writeFile(abs, next, 'utf8')
  return { ok: true, diff: `replaced 1 occurrence in ${path.basename(abs)}` }
}

async function insert(abs: string, line: number, text: string): Promise<EditResult> {
  const content = await readFile(abs, 'utf8')
  const lines = content.split('\n')
  if (line < 0 || line > lines.length) {
    return { ok: false, error: `insert_line ${line} out of range (0..${lines.length})` }
  }
  lines.splice(line, 0, text)
  await writeFile(abs, lines.join('\n'), 'utf8')
  return { ok: true, diff: `inserted at line ${line} of ${path.basename(abs)}` }
}

function occurrences(haystack: string, needle: string): number {
  let n = 0
  let i = haystack.indexOf(needle)
  while (i !== -1) {
    n++
    i = haystack.indexOf(needle, i + needle.length)
  }
  return n
}
