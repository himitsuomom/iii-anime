/**
 * Workspace materialization: write a generated codebase to a temp directory so
 * an executor can run it. Path safety (`isSafeRelativePath`) is shared with the
 * artifact builder in `logic/artifacts.ts`.
 */

import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { type GeneratedFile, isSafeRelativePath } from './logic/artifacts'

export { isSafeRelativePath }

/** Create a fresh empty temp workspace and return its absolute path. */
export async function createWorkspace(prefix = 'saas-replicator-'): Promise<string> {
  return mkdtemp(join(tmpdir(), prefix))
}

/**
 * Write each file under `root`, creating parent directories. Unsafe paths
 * (absolute / `..` escapes) are skipped. Returns the relative paths written.
 */
export async function materialize(files: GeneratedFile[], root: string): Promise<string[]> {
  const written: string[] = []
  for (const file of files) {
    if (!isSafeRelativePath(file.path)) continue
    const abs = join(root, file.path)
    await mkdir(dirname(abs), { recursive: true })
    await writeFile(abs, file.content, 'utf8')
    written.push(file.path)
  }
  return written
}

/** Remove a workspace directory (best-effort). */
export async function cleanup(root: string): Promise<void> {
  await rm(root, { recursive: true, force: true })
}
