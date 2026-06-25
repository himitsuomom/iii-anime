// The iii-sdk does not export a Logger class — logging flows through `console.*`,
// which the SDK captures via its OpenTelemetry instrumentation. This is a tiny
// drop-in used by the examples to keep structured, function-labeled log lines.

type Meta = Record<string, unknown>

export class Logger {
  private readonly label?: string

  constructor(_level?: unknown, label?: string) {
    this.label = label
  }

  private format(message: string): string {
    return this.label ? `[${this.label}] ${message}` : message
  }

  info(message: string, meta?: Meta): void {
    meta ? console.info(this.format(message), meta) : console.info(this.format(message))
  }

  warn(message: string, meta?: Meta): void {
    meta ? console.warn(this.format(message), meta) : console.warn(this.format(message))
  }

  error(message: string, meta?: Meta): void {
    meta ? console.error(this.format(message), meta) : console.error(this.format(message))
  }
}
