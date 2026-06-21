// ffmpeg render: assemble a storyboard's images (each shown for N seconds) into
// an mp4, optionally muxing background audio. Pure arg builders here; execution
// goes through the shared sandbox (see ../sandbox.ts). The pure builders are
// unit-tested without ffmpeg installed.
import type { Storyboard } from '../types.js'

/**
 * ffmpeg argv that turns one image into a clip of the given duration.
 * (One clip per shot; clips are concatenated by buildConcatArgs.)
 */
export function imageClipArgs(image: string, seconds: number, out: string): string[] {
  return [
    '-y',
    '-loop', '1',
    '-t', String(seconds),
    '-i', image,
    '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:-1:-1,format=yuv420p',
    '-r', '30',
    out,
  ]
}

/** ffmpeg argv that concatenates clips (via a concat list file) into the output. */
export function concatArgs(listFile: string, output: string, audio?: string): string[] {
  const args = ['-y', '-f', 'concat', '-safe', '0', '-i', listFile]
  if (audio) args.push('-i', audio, '-shortest')
  args.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', output)
  return args
}

/** Lines for the ffmpeg concat demuxer list file (one per clip). */
export function concatListFile(clips: string[]): string {
  return clips.map((c) => `file '${c}'`).join('\n') + '\n'
}

/** Plan a full render: per-shot clip commands + the final concat command. */
export interface RenderPlan {
  clips: Array<{ out: string; args: string[] }>
  listFile: { path: string; content: string }
  concat: string[]
}

export function planRender(sb: Storyboard): RenderPlan {
  const clips = sb.shots.map((shot, i) => {
    const out = `clip_${i}.mp4`
    return { out, args: imageClipArgs(shot.image, shot.seconds, out) }
  })
  const listPath = 'concat.txt'
  return {
    clips,
    listFile: { path: listPath, content: concatListFile(clips.map((c) => c.out)) },
    concat: concatArgs(listPath, sb.output, sb.audio),
  }
}
