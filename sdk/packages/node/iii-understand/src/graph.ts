import { readFileSync, statSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'
import type { GraphEdge, GraphNode, KnowledgeGraph } from './types'

/**
 * Resolve the on-disk location of the knowledge graph. Precedence:
 *   1. `UNDERSTAND_GRAPH_PATH` — explicit file path (absolute or cwd-relative)
 *   2. `UNDERSTAND_REPO_ROOT`  — directory containing `.understand-anything/`
 *   3. process cwd
 */
export function resolveGraphPath(env: NodeJS.ProcessEnv = process.env): string {
  const explicit = env.UNDERSTAND_GRAPH_PATH
  if (explicit && explicit.trim() !== '') {
    return isAbsolute(explicit) ? explicit : join(process.cwd(), explicit)
  }
  const root =
    env.UNDERSTAND_REPO_ROOT && env.UNDERSTAND_REPO_ROOT.trim() !== ''
      ? env.UNDERSTAND_REPO_ROOT
      : process.cwd()
  return join(root, '.understand-anything', 'knowledge-graph.json')
}

interface CacheEntry {
  mtimeMs: number
  graph: KnowledgeGraph
}

const cache = new Map<string, CacheEntry>()

/** Clear the in-memory graph cache (used by tests and the refresh function). */
export function clearGraphCache(): void {
  cache.clear()
}

/**
 * Load and parse the knowledge graph, caching by file mtime so repeated queries
 * are cheap but a re-run of `/understand` is picked up automatically. Throws a
 * {@link GraphNotFoundError} when no graph file exists yet.
 */
export function loadGraph(path: string = resolveGraphPath()): KnowledgeGraph {
  let mtimeMs: number
  try {
    mtimeMs = statSync(path).mtimeMs
  } catch {
    throw new GraphNotFoundError(path)
  }
  const cached = cache.get(path)
  if (cached && cached.mtimeMs === mtimeMs) {
    return cached.graph
  }
  const graph = JSON.parse(readFileSync(path, 'utf8')) as KnowledgeGraph
  cache.set(path, { mtimeMs, graph })
  return graph
}

export class GraphNotFoundError extends Error {
  constructor(public readonly path: string) {
    super(
      `No knowledge graph found at ${path}. Run the Understand-Anything \`/understand\` skill in the target repo first, ` +
        `or set UNDERSTAND_GRAPH_PATH / UNDERSTAND_REPO_ROOT.`,
    )
    this.name = 'GraphNotFoundError'
  }
}

// ---------------------------------------------------------------------------
// Pure query helpers — operate on an already-loaded graph so they are trivially
// testable without touching the filesystem or the engine.
// ---------------------------------------------------------------------------

export interface GraphStatus {
  exists: true
  path: string
  project: KnowledgeGraph['project']
  version: string
  kind: KnowledgeGraph['kind']
  counts: { nodes: number; edges: number; layers: number; tourSteps: number }
}

export function status(graph: KnowledgeGraph, path: string): GraphStatus {
  return {
    exists: true,
    path,
    project: graph.project,
    version: graph.version,
    kind: graph.kind,
    counts: {
      nodes: graph.nodes.length,
      edges: graph.edges.length,
      layers: graph.layers.length,
      tourSteps: graph.tour.length,
    },
  }
}

export interface Overview {
  project: KnowledgeGraph['project']
  nodeTypeBreakdown: Record<string, number>
  layers: Array<{ id: string; name: string; description: string; nodeCount: number }>
}

export function overview(graph: KnowledgeGraph): Overview {
  const nodeTypeBreakdown: Record<string, number> = {}
  for (const node of graph.nodes) {
    nodeTypeBreakdown[node.type] = (nodeTypeBreakdown[node.type] ?? 0) + 1
  }
  return {
    project: graph.project,
    nodeTypeBreakdown,
    layers: graph.layers.map(l => ({
      id: l.id,
      name: l.name,
      description: l.description,
      nodeCount: l.nodeIds.length,
    })),
  }
}

export interface SearchParams {
  query: string
  type?: string
  layer?: string
  limit?: number
}

export interface SearchHit {
  id: string
  type: string
  name: string
  filePath?: string
  summary: string
  tags: string[]
  score: number
}

/**
 * Rank nodes against a free-text query. Scoring is deterministic and weighted:
 * exact name match > name prefix > name substring > path/tag > summary. A `type`
 * and/or `layer` filter narrows the candidate set before scoring.
 */
export function search(graph: KnowledgeGraph, params: SearchParams): SearchHit[] {
  const q = params.query.trim().toLowerCase()
  const limit = params.limit && params.limit > 0 ? params.limit : 20

  let candidates = graph.nodes
  if (params.type) {
    candidates = candidates.filter(n => n.type === params.type)
  }
  if (params.layer) {
    const layer = graph.layers.find(l => l.id === params.layer || l.name === params.layer)
    const ids = new Set(layer?.nodeIds ?? [])
    candidates = candidates.filter(n => ids.has(n.id))
  }

  if (q === '') {
    return candidates.slice(0, limit).map(n => ({ ...toHit(n), score: 0 }))
  }

  const hits: SearchHit[] = []
  for (const node of candidates) {
    const score = scoreNode(node, q)
    if (score > 0) {
      hits.push({ ...toHit(node), score })
    }
  }
  hits.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))
  return hits.slice(0, limit)
}

function toHit(node: GraphNode): Omit<SearchHit, 'score'> {
  return {
    id: node.id,
    type: node.type,
    name: node.name,
    filePath: node.filePath,
    summary: node.summary,
    tags: node.tags,
  }
}

function scoreNode(node: GraphNode, q: string): number {
  const name = node.name.toLowerCase()
  if (name === q) return 100
  if (name.startsWith(q)) return 70
  if (name.includes(q)) return 50
  if (node.filePath?.toLowerCase().includes(q)) return 30
  if (node.tags.some(t => t.toLowerCase().includes(q))) return 25
  if (node.summary.toLowerCase().includes(q)) return 10
  return 0
}

export interface NodeDetail {
  node: GraphNode
  layers: string[]
  outgoing: Array<{ edge: GraphEdge; node?: { id: string; name: string; type: string } }>
  incoming: Array<{ edge: GraphEdge; node?: { id: string; name: string; type: string } }>
}

export function getNode(graph: KnowledgeGraph, id: string): NodeDetail | null {
  const node = graph.nodes.find(n => n.id === id)
  if (!node) return null
  const index = new Map(graph.nodes.map(n => [n.id, n]))
  const ref = (nid: string) => {
    const n = index.get(nid)
    return n ? { id: n.id, name: n.name, type: n.type } : undefined
  }
  return {
    node,
    layers: graph.layers.filter(l => l.nodeIds.includes(id)).map(l => l.name),
    outgoing: graph.edges.filter(e => e.source === id).map(e => ({ edge: e, node: ref(e.target) })),
    incoming: graph.edges.filter(e => e.target === id).map(e => ({ edge: e, node: ref(e.source) })),
  }
}

export interface NeighborParams {
  id: string
  direction?: 'in' | 'out' | 'both'
  edgeType?: string
}

export interface Neighbor {
  id: string
  name: string
  type: string
  via: string
  direction: 'in' | 'out'
  weight: number
}

export function neighbors(graph: KnowledgeGraph, params: NeighborParams): Neighbor[] {
  const direction = params.direction ?? 'both'
  const index = new Map(graph.nodes.map(n => [n.id, n]))
  const out: Neighbor[] = []
  for (const edge of graph.edges) {
    if (params.edgeType && edge.type !== params.edgeType) continue
    if ((direction === 'out' || direction === 'both') && edge.source === params.id) {
      const n = index.get(edge.target)
      if (n)
        out.push({
          id: n.id,
          name: n.name,
          type: n.type,
          via: edge.type,
          direction: 'out',
          weight: edge.weight,
        })
    }
    if ((direction === 'in' || direction === 'both') && edge.target === params.id) {
      const n = index.get(edge.source)
      if (n)
        out.push({
          id: n.id,
          name: n.name,
          type: n.type,
          via: edge.type,
          direction: 'in',
          weight: edge.weight,
        })
    }
  }
  return out
}

export interface Explanation {
  node: GraphNode
  layers: string[]
  dependsOn: Array<{ id: string; name: string; via: string }>
  usedBy: Array<{ id: string; name: string; via: string }>
}

/**
 * Resolve a node by id or by (partial) file path, then return a deep-dive view:
 * its summary plus what it depends on and what depends on it.
 */
export function explain(
  graph: KnowledgeGraph,
  target: { id?: string; file?: string },
): Explanation | null {
  let node: GraphNode | undefined
  if (target.id) {
    node = graph.nodes.find(n => n.id === target.id)
  } else if (target.file) {
    const f = target.file.toLowerCase()
    node =
      graph.nodes.find(n => n.filePath?.toLowerCase() === f) ??
      graph.nodes.find(n => n.filePath?.toLowerCase().includes(f))
  }
  if (!node) return null
  const detail = getNode(graph, node.id)
  const relate = (edges: NodeDetail['outgoing']) =>
    edges.flatMap(e => (e.node ? [{ id: e.node.id, name: e.node.name, via: e.edge.type }] : []))
  return {
    node,
    layers: detail?.layers ?? [],
    dependsOn: relate(detail?.outgoing ?? []),
    usedBy: relate(detail?.incoming ?? []),
  }
}

export function tour(graph: KnowledgeGraph): KnowledgeGraph['tour'] {
  return [...graph.tour].sort((a, b) => a.order - b.order)
}
