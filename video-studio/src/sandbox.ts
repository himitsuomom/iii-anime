// The video factory reuses app-studio's hardened sandbox verbatim — the
// allowlist + workdir-confinement + timeout + optional unshare isolation are
// the de-facto "studio-core" shared across factories. Only the allowlist
// differs (video tools instead of build tools).
export {
  execInWorkspace,
  editInWorkspace,
  ensureWorkspace,
  listWorkspaceFiles,
  workspaceDir,
  parseCommand,
  SandboxCommandError,
} from '../../studio-core/src/sandbox/index.js'

/** Executables the render agent may run in a workdir. */
export const VIDEO_ALLOWLIST: ReadonlySet<string> = new Set([
  'ffmpeg',
  'ffprobe',
  'node',
  'ls',
  'cat',
  'mkdir',
  'cp',
  'mv',
  'rm',
  'test',
  'echo',
  'true',
])
