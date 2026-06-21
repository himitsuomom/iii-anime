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
