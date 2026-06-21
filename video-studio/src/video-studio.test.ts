import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, test } from 'node:test'
import { videoRubric, durationWithinTolerance } from './qa.js'
import { concatArgs, concatListFile, imageClipArgs, planRender } from './render/ffmpeg.js'
import { execInWorkspace, parseCommand, SandboxCommandError, VIDEO_ALLOWLIST } from './sandbox.js'
import { validateStoryboard } from './storyboard.js'
import type { Storyboard } from './types.js'

const SB: Storyboard = {
  title: 'Promo',
  output: 'out.mp4',
  shots: [
    { image: 'a.png', seconds: 2 },
    { image: 'b.png', seconds: 3, caption: 'hi' },
  ],
}

describe('shared sandbox (reused from app-studio) with the video allowlist', () => {
  let base: string
  beforeEach(async () => {
    base = await mkdtemp(path.join(os.tmpdir(), 'video-sb-'))
    process.env.STUDIO_WORK_ROOT = base
  })
  afterEach(async () => {
    await rm(base, { recursive: true, force: true })
    delete process.env.STUDIO_WORK_ROOT
  })

  test('allows video tools and runs a command through the shared sandbox', async () => {
    assert.deepEqual(parseCommand('ffmpeg -version', VIDEO_ALLOWLIST), {
      file: 'ffmpeg',
      args: ['-version'],
    })
    const r = await execInWorkspace({ project_id: 'vid_1', cmd: 'echo ok', allowlist: VIDEO_ALLOWLIST })
    assert.equal(r.exit_code, 0)
    assert.equal(r.stdout.trim(), 'ok')
  })

  test('still rejects non-allowlisted executables and shell operators', () => {
    assert.throws(() => parseCommand('curl http://evil', VIDEO_ALLOWLIST), SandboxCommandError)
    assert.throws(() => parseCommand('ffmpeg -i a && rm -rf /', VIDEO_ALLOWLIST), SandboxCommandError)
  })
})

describe('storyboard validation', () => {
  test('accepts a well-formed storyboard', () => {
    const sb = validateStoryboard(SB)
    assert.equal(sb.shots.length, 2)
    assert.equal(sb.output, 'out.mp4')
  })
  test('rejects empty shots and non-positive durations', () => {
    assert.throws(() => validateStoryboard({ title: 't', output: 'o.mp4', shots: [] }))
    assert.throws(() =>
      validateStoryboard({ title: 't', output: 'o.mp4', shots: [{ image: 'a.png', seconds: 0 }] }),
    )
  })
})

describe('ffmpeg arg builders', () => {
  test('imageClipArgs loops one image for the duration', () => {
    const a = imageClipArgs('a.png', 2, 'clip_0.mp4')
    assert.deepEqual(a.slice(0, 6), ['-y', '-loop', '1', '-t', '2', '-i'])
    assert.equal(a.at(-1), 'clip_0.mp4')
    assert.ok(a.includes('a.png'))
  })
  test('concatArgs muxes audio only when provided', () => {
    assert.ok(!concatArgs('list.txt', 'o.mp4').includes('-shortest'))
    assert.ok(concatArgs('list.txt', 'o.mp4', 'bg.mp3').includes('-shortest'))
  })
  test('concatListFile escapes one entry per clip', () => {
    assert.equal(concatListFile(['clip_0.mp4', 'clip_1.mp4']), "file 'clip_0.mp4'\nfile 'clip_1.mp4'\n")
  })
  test('planRender produces a clip per shot plus a concat step', () => {
    const plan = planRender(SB)
    assert.equal(plan.clips.length, 2)
    assert.equal(plan.listFile.path, 'concat.txt')
    assert.ok(plan.concat.includes('out.mp4'))
  })
})

describe('video QA (objective checks + tolerance)', () => {
  test('rubric checks output existence and ffprobe', () => {
    const r = videoRubric(SB)
    assert.deepEqual(
      r.map((c) => c.id),
      ['output-exists', 'probe'],
    )
    assert.match(r[0]!.cmd, /test -f out\.mp4/)
  })
  test('duration tolerance', () => {
    assert.equal(durationWithinTolerance(5, 5.2), true)
    assert.equal(durationWithinTolerance(5, 9), false)
    assert.equal(durationWithinTolerance(0, 1), true)
  })
})
