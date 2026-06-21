import type { Engine } from './engine'

/** Result shape returned by `sandbox::run` (see iii-worker sandbox_daemon). */
export interface SandboxResult {
  stdout: string
  stderr: string
  exit_code: number
  success: boolean
  timed_out?: boolean
  duration_ms?: number
}

export type SandboxLang = 'node' | 'python' | 'shell'

/** Run a one-shot script in an ephemeral microVM via the `iii-sandbox` worker. */
export async function runInSandbox(
  engine: Engine,
  opts: { lang: SandboxLang; code: string; image?: string },
): Promise<SandboxResult> {
  return engine.call<SandboxResult>('sandbox::run', {
    image: opts.image ?? opts.lang,
    lang: opts.lang,
    code: opts.code,
  })
}

/** True when an `iii-sandbox` worker is registered (so tests can run isolated). */
export async function sandboxAvailable(engine: Engine): Promise<boolean> {
  try {
    const workers = await engine.listWorkers()
    return workers.some((w) => typeof w?.name === 'string' && w.name.includes('iii-sandbox'))
  } catch {
    return false
  }
}
