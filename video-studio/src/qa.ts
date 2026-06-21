// Video QA. Unlike software (tests pass = objectively done), "good video" is
// subjective — so the rubric checks only objective properties (the output
// exists and is a valid, non-empty video of roughly the intended length), and
// the factory leans on the human approval gate for the creative judgement.
import type { Storyboard } from './types.js'

export interface RubricCheck {
  id: string
  cmd: string
  expect: 'exit0'
}

/** Objective checks: the output file exists and ffprobe can read a duration. */
export function videoRubric(sb: Storyboard): RubricCheck[] {
  return [
    { id: 'output-exists', cmd: `test -f ${sb.output}`, expect: 'exit0' },
    {
      id: 'probe',
      cmd: `ffprobe -v error -show_entries format=duration -of csv=p=0 ${sb.output}`,
      expect: 'exit0',
    },
  ]
}

/** Did the probed duration land within tolerance of the intended length? */
export function durationWithinTolerance(
  intended: number,
  probed: number,
  tolerance = 0.5,
): boolean {
  if (intended <= 0) return probed > 0
  return Math.abs(probed - intended) / intended <= tolerance
}
