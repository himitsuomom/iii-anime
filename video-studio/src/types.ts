// Video factory domain types. The pipeline mirrors app-studio's shape
// (brief → storyboard → render → QA → approval → deliver) but the medium is
// video, so "done" is checked very differently (see qa.ts).

export interface Brief {
  goal: string
  duration_seconds: number
  /** One line per intended shot/scene. */
  shots: string[]
  assumptions: string[]
}

export interface Shot {
  /** Source image file (relative to the workdir). */
  image: string
  caption?: string
  seconds: number
}

export interface Storyboard {
  title: string
  shots: Shot[]
  /** Optional background audio file. */
  audio?: string
  /** Output video file the render must produce. */
  output: string
}

export interface VideoQa {
  passed: boolean
  failures: string[]
  /** Probed duration in seconds, if the output was produced. */
  duration_seconds?: number
}
