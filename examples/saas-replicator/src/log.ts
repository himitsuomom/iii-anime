/**
 * Minimal logger. The published `iii-sdk` does not export a `Logger`, so we use
 * a tiny console-backed shim with the same `info/warn/error(msg, meta?)` shape.
 */
export class Logger {
  constructor(
    private readonly _unused?: unknown,
    private readonly scope?: string,
  ) {}

  private emit(level: string, msg: string, meta?: Record<string, unknown>) {
    const prefix = this.scope ? `[${this.scope}]` : ''
    if (meta) console.log(`${level} ${prefix} ${msg}`, JSON.stringify(meta))
    else console.log(`${level} ${prefix} ${msg}`)
  }

  info(msg: string, meta?: Record<string, unknown>) {
    this.emit('INFO', msg, meta)
  }
  warn(msg: string, meta?: Record<string, unknown>) {
    this.emit('WARN', msg, meta)
  }
  error(msg: string, meta?: Record<string, unknown>) {
    this.emit('ERROR', msg, meta)
  }
}
