// Workspace confinement: every sandbox operation is locked to a per-project
// workdir. Paths are resolved lexically and re-checked against the root so a
// crafted `path` (../, absolute, symlink) can never escape.
import { mkdir, realpath } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

/** Base directory that holds every project's workdir. Overridable for tests. */
export function workRoot(): string {
  return process.env.STUDIO_WORK_ROOT ?? path.join(os.tmpdir(), 'iii-studio-work')
}

/** Absolute workdir for a project. Project ids are validated to be a single safe segment. */
export function workspaceDir(projectId: string): string {
  if (!/^[A-Za-z0-9_-]+$/.test(projectId)) {
    throw new SandboxPathError(`invalid project_id: ${projectId}`)
  }
  return path.join(workRoot(), projectId)
}

export class SandboxPathError extends Error {}

/**
 * Resolve a project-relative path and guarantee it stays inside the workdir.
 * Works for paths that don't exist yet (create): we resolve lexically, then,
 * if the nearest existing ancestor is a symlink, re-validate via realpath.
 */
export async function resolveInside(projectId: string, rel: string): Promise<string> {
  const root = workspaceDir(projectId)
  if (path.isAbsolute(rel)) {
    throw new SandboxPathError(`absolute paths are not allowed: ${rel}`)
  }
  const resolved = path.resolve(root, rel)
  if (!isInside(root, resolved)) {
    throw new SandboxPathError(`path escapes workspace: ${rel}`)
  }
  // Defend against symlinked ancestors pointing outside the root. The workdir
  // may not exist yet (create), so canonicalize via the nearest existing ancestor.
  const realRoot = (await realpathOfNearestExisting(root)) ?? root
  const realAncestor = await realpathOfNearestExisting(resolved)
  if (realAncestor !== null && !isInside(realRoot, realAncestor)) {
    throw new SandboxPathError(`path escapes workspace via symlink: ${rel}`)
  }
  return resolved
}

/** Create the project workdir (idempotent). */
export async function ensureWorkspace(projectId: string): Promise<string> {
  const dir = workspaceDir(projectId)
  await mkdir(dir, { recursive: true })
  return dir
}

function isInside(root: string, p: string): boolean {
  const rel = path.relative(root, p)
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))
}

async function realpathOfNearestExisting(p: string): Promise<string | null> {
  let cur = p
  // Walk up until an existing ancestor is found, realpath it, then re-append the tail.
  const tail: string[] = []
  // eslint-disable-next-line no-constant-condition
  while (true) {
    try {
      const real = await realpath(cur)
      return tail.length ? path.join(real, ...tail.reverse()) : real
    } catch {
      const parent = path.dirname(cur)
      if (parent === cur) return null
      tail.push(path.basename(cur))
      cur = parent
    }
  }
}
