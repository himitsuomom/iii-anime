// Secret access for host-side steps (e.g. a git push token at deliver). The key
// rule: secrets are fetched on the orchestrator/host side and are NEVER injected
// into the sandbox env (sandbox::exec passes only PATH/HOME/CI). Production:
// back this with a real secrets manager / iii Vault; EnvSecretStore is the dev
// default reading STUDIO_SECRET_<NAME>.
export interface SecretStore {
  get(name: string): Promise<string | null>
}

export class EnvSecretStore implements SecretStore {
  constructor(
    private env: NodeJS.ProcessEnv = process.env,
    private prefix = 'STUDIO_SECRET_',
  ) {}

  async get(name: string): Promise<string | null> {
    const key = this.prefix + name.toUpperCase().replace(/[^A-Z0-9]/g, '_')
    return this.env[key] ?? null
  }
}

/** Guard: assert a secrets bundle never leaks into an env handed to the sandbox. */
export function assertNoSecretsInEnv(
  env: Record<string, string | undefined>,
  prefix = 'STUDIO_SECRET_',
): void {
  for (const k of Object.keys(env)) {
    if (k.startsWith(prefix) || k === 'STUDIO_API_TOKEN') {
      throw new Error(`secret ${k} must not be passed to the sandbox`)
    }
  }
}
