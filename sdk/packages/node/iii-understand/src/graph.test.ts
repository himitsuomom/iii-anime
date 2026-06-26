import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearGraphCache,
  explain,
  getNode,
  GraphNotFoundError,
  loadGraph,
  neighbors,
  overview,
  resolveGraphPath,
  search,
  status,
  tour,
} from './graph'

const here = dirname(fileURLToPath(import.meta.url))
const FIXTURE = join(here, '..', 'fixtures', 'sample-knowledge-graph.json')

describe('loadGraph', () => {
  beforeEach(() => clearGraphCache())

  it('loads and caches the fixture', () => {
    const a = loadGraph(FIXTURE)
    const b = loadGraph(FIXTURE)
    expect(a).toBe(b) // same cached reference
    expect(a.nodes).toHaveLength(5)
  })

  it('throws GraphNotFoundError for a missing file', () => {
    expect(() => loadGraph('/nope/does-not-exist.json')).toThrow(GraphNotFoundError)
  })
})

describe('resolveGraphPath', () => {
  it('honors UNDERSTAND_GRAPH_PATH (absolute)', () => {
    expect(
      resolveGraphPath({ UNDERSTAND_GRAPH_PATH: '/abs/graph.json' } as NodeJS.ProcessEnv),
    ).toBe('/abs/graph.json')
  })
  it('derives from UNDERSTAND_REPO_ROOT', () => {
    expect(resolveGraphPath({ UNDERSTAND_REPO_ROOT: '/repo' } as NodeJS.ProcessEnv)).toBe(
      '/repo/.understand-anything/knowledge-graph.json',
    )
  })
})

describe('queries', () => {
  const graph = loadGraph(FIXTURE)

  it('status reports counts', () => {
    const s = status(graph, FIXTURE)
    expect(s.counts).toEqual({ nodes: 5, edges: 6, layers: 2, tourSteps: 2 })
    expect(s.project.name).toBe('sample-orders-service')
  })

  it('overview breaks down node types and layers', () => {
    const o = overview(graph)
    expect(o.nodeTypeBreakdown.function).toBe(2)
    expect(o.nodeTypeBreakdown.file).toBe(2)
    expect(o.layers.find(l => l.id === 'layer:domain')?.nodeCount).toBe(3)
  })

  it('search ranks exact name matches highest', () => {
    const hits = search(graph, { query: 'saveOrder' })
    expect(hits[0].id).toBe('fn:saveOrder')
    expect(hits[0].score).toBe(100)
  })

  it('search filters by type', () => {
    const hits = search(graph, { query: 'order', type: 'function' })
    expect(hits.every(h => h.type === 'function')).toBe(true)
  })

  it('search filters by layer', () => {
    const hits = search(graph, { query: '', layer: 'layer:infra' })
    const ids = hits.map(h => h.id).sort()
    expect(ids).toEqual(['ep:POST /orders', 'file:src/db.ts'])
  })

  it('getNode returns incoming and outgoing edges', () => {
    const detail = getNode(graph, 'fn:saveOrder')
    expect(detail).not.toBeNull()
    expect(detail?.outgoing.map(o => o.node?.id).sort()).toEqual([
      'file:src/db.ts',
      'fn:validateOrder',
    ])
    expect(detail?.incoming.map(i => i.node?.id).sort()).toEqual([
      'ep:POST /orders',
      'file:src/orders.ts',
    ])
    expect(detail?.layers).toContain('Domain')
  })

  it('getNode returns null for unknown id', () => {
    expect(getNode(graph, 'nope')).toBeNull()
  })

  it('neighbors respects direction and edgeType', () => {
    const callers = neighbors(graph, { id: 'fn:validateOrder', direction: 'in', edgeType: 'calls' })
    expect(callers.map(n => n.id).sort()).toEqual(['ep:POST /orders', 'fn:saveOrder'])
    expect(callers.every(n => n.direction === 'in' && n.via === 'calls')).toBe(true)
  })

  it('explain resolves by file path substring', () => {
    const e = explain(graph, { file: 'orders.ts' })
    expect(e?.node.id).toBe('file:src/orders.ts')
    expect(e?.dependsOn.map(d => d.id).sort()).toEqual(['fn:saveOrder', 'fn:validateOrder'])
  })

  it('explain resolves by id with usedBy', () => {
    const e = explain(graph, { id: 'fn:validateOrder' })
    // incoming edges: file contains it, saveOrder + endpoint call it
    expect(e?.usedBy.map(u => u.id).sort()).toEqual([
      'ep:POST /orders',
      'file:src/orders.ts',
      'fn:saveOrder',
    ])
  })

  it('tour is ordered', () => {
    const steps = tour(graph)
    expect(steps.map(s => s.order)).toEqual([1, 2])
  })
})
