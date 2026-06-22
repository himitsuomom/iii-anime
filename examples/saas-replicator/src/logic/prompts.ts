/**
 * Pure prompt builders. Each returns a `messages` array with an explicit JSON
 * output contract so `parseJsonFromContent` can turn the response into a typed
 * artifact. Kept dependency-free and unit-testable.
 */

export interface Message {
  role: 'system' | 'user'
  content: string
  image?: string
}

const jsonContract = (shape: string) =>
  `Respond ONLY with a JSON object of the form ${shape}. No prose, no code fences.`

export function analyzeScreenPrompt(screen: { id: string; source?: string }): Message[] {
  return [
    { role: 'system', content: 'You are a UI analyst. Extract components and design tokens from a screenshot.' },
    {
      role: 'user',
      content: `Analyze screen "${screen.id}". ${jsonContract('{ "components": string[], "tokens": { "colors": string[], "fonts": string[], "spacing": number[] }, "notes": string }')}`,
      image: screen.source,
    },
  ]
}

export function prdPrompt(target: string, requirements: string): Message[] {
  return [
    { role: 'system', content: 'You are a product director. Write a concise PRD.' },
    {
      role: 'user',
      content: `Target SaaS: ${target}. Requirements: ${requirements}. ${jsonContract('{ "summary": string, "features": string[], "dataModel": string[] }')}`,
    },
  ]
}

export function implementationPrompt(target: string): Message[] {
  return [
    { role: 'system', content: 'You are a senior engineer. Outline the implementation file plan.' },
    {
      role: 'user',
      content: `Implement ${target} (frontend, backend, auth). ${jsonContract('{ "files": string[], "notes": string }')}`,
    },
  ]
}

export function codebasePrompt(target: string): Message[] {
  return [
    { role: 'system', content: 'You are a senior engineer. Generate a small, runnable codebase scaffold.' },
    {
      role: 'user',
      content: `Generate the codebase to rebuild ${target}: source files plus a runnable Node test file (ESM .mjs) that prints a line "TESTS total=<n> passed=<n> failed=<n>". ${jsonContract('{ "files": [{ "path": string, "content": string }], "testFile": string }')}`,
    },
  ]
}

export function vizPrompt(spec: unknown): Message[] {
  return [
    { role: 'system', content: 'You produce mermaid diagrams.' },
    {
      role: 'user',
      content: `Produce a mermaid diagram for: ${JSON.stringify(spec)}. ${jsonContract('{ "source": string }')}`,
    },
  ]
}

export function deployPrompt(target: string): Message[] {
  return [
    { role: 'system', content: 'You prepare deployment + PWA configuration.' },
    {
      role: 'user',
      content: `Prepare deployment for ${target}. ${jsonContract('{ "url": string, "pwa": boolean, "notes": string }')}`,
    },
  ]
}

/** Supervisor: grade an artifact and (when failing) say how to improve it. */
export function critiquePrompt(target: string, artifact: unknown): Message[] {
  return [
    { role: 'system', content: 'You are a strict reviewer. Critique the artifact and score its quality.' },
    {
      role: 'user',
      content: `Critique this artifact for ${target}: ${JSON.stringify(artifact)}. Give a quality score in [0,1]. ${jsonContract('{ "score": number, "pass": boolean, "feedback": string }')}`,
    },
  ]
}

/** Debate / self-critique: argue a position on an open question. */
export function debatePrompt(question: string, stance?: string): Message[] {
  const role = stance ? `Argue the "${stance}" position.` : 'Take a position and defend it.'
  return [
    { role: 'system', content: 'You are an expert participating in a debate to reach the best decision.' },
    {
      role: 'user',
      content: `Debate question: ${question}. ${role} ${jsonContract('{ "answer": string, "rationale": string }')}`,
    },
  ]
}

/** Judge: synthesize competing debate answers into a final decision. */
export function synthesizePrompt(question: string, positions: unknown[]): Message[] {
  return [
    { role: 'system', content: 'You are an impartial judge. Synthesize the strongest decision from the positions.' },
    {
      role: 'user',
      content: `Question: ${question}. Positions: ${JSON.stringify(positions)}. Synthesize the best answer. ${jsonContract('{ "answer": string, "rationale": string }')}`,
    },
  ]
}
