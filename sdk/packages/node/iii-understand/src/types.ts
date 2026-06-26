// KnowledgeGraph schema produced by the Understand-Anything `/understand` skill
// (written to `.understand-anything/knowledge-graph.json`). This is a trimmed,
// runtime-focused copy of the producer's type surface — only the fields this
// worker reads are kept. See the upstream plugin's `packages/core/src/types.ts`
// for the full definition.

export type NodeType =
  | 'file'
  | 'function'
  | 'class'
  | 'module'
  | 'concept'
  | 'config'
  | 'document'
  | 'service'
  | 'table'
  | 'endpoint'
  | 'pipeline'
  | 'schema'
  | 'resource'
  | 'domain'
  | 'flow'
  | 'step'
  | 'article'
  | 'entity'
  | 'topic'
  | 'claim'
  | 'source'

export type EdgeDirection = 'forward' | 'backward' | 'bidirectional'

export interface GraphNode {
  id: string
  type: NodeType
  name: string
  filePath?: string
  lineRange?: [number, number]
  summary: string
  tags: string[]
  complexity: 'simple' | 'moderate' | 'complex'
  languageNotes?: string
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  direction: EdgeDirection
  description?: string
  weight: number
}

export interface Layer {
  id: string
  name: string
  description: string
  nodeIds: string[]
}

export interface TourStep {
  order: number
  title: string
  description: string
  nodeIds: string[]
  languageLesson?: string
}

export interface ProjectMeta {
  name: string
  languages: string[]
  frameworks: string[]
  description: string
  analyzedAt: string
  gitCommitHash: string
}

export interface KnowledgeGraph {
  version: string
  kind?: 'codebase' | 'knowledge'
  project: ProjectMeta
  nodes: GraphNode[]
  edges: GraphEdge[]
  layers: Layer[]
  tour: TourStep[]
}
