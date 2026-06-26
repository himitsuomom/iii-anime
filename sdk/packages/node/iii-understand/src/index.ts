import { Logger } from '@iii-dev/observability'
import {
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
import { iii } from './iii'

// The `understand` worker turns an Understand-Anything knowledge graph
// (`.understand-anything/knowledge-graph.json`) into iii functions + HTTP
// triggers, so any other worker or agent can query a codebase's structure
// through the engine instead of re-reading files.

const logger = new Logger(undefined, 'understand')

function firstParam(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0]
  return value
}

/** Load the graph or translate a missing graph into a 404-friendly result. */
function withGraph<T>(
  fn: (graph: ReturnType<typeof loadGraph>, path: string) => T,
): T | { status_code: 404; body: { error: string } } {
  const path = resolveGraphPath()
  try {
    const graph = loadGraph(path)
    return fn(graph, path)
  } catch (err) {
    if (err instanceof GraphNotFoundError) {
      return { status_code: 404, body: { error: err.message } }
    }
    throw err
  }
}

// --- understand::status -----------------------------------------------------
iii.registerFunction(
  'understand::status',
  async () => {
    const path = resolveGraphPath()
    try {
      const graph = loadGraph(path)
      return status(graph, path)
    } catch (err) {
      if (err instanceof GraphNotFoundError) {
        return { exists: false as const, path, message: err.message }
      }
      throw err
    }
  },
  { description: 'Report whether a knowledge graph exists and its project metadata + counts' },
)

// --- understand::overview ---------------------------------------------------
iii.registerFunction('understand::overview', async () => withGraph(g => overview(g)), {
  description: 'Project metadata, node-type breakdown, and logical layers',
})

// --- understand::search -----------------------------------------------------
iii.registerFunction(
  'understand::search',
  async (input: { query?: string; type?: string; layer?: string; limit?: number }) =>
    withGraph(g =>
      search(g, {
        query: input?.query ?? '',
        type: input?.type,
        layer: input?.layer,
        limit: input?.limit,
      }),
    ),
  { description: 'Rank graph nodes against a free-text query, optionally filtered by type/layer' },
)

// --- understand::node -------------------------------------------------------
iii.registerFunction(
  'understand::node',
  async (input: { id?: string }) =>
    withGraph(g => {
      if (!input?.id) return { status_code: 400 as const, body: { error: 'id is required' } }
      const detail = getNode(g, input.id)
      return detail ?? { status_code: 404 as const, body: { error: `node not found: ${input.id}` } }
    }),
  { description: 'Get a node with its layers and incoming/outgoing edges' },
)

// --- understand::neighbors --------------------------------------------------
iii.registerFunction(
  'understand::neighbors',
  async (input: { id?: string; direction?: 'in' | 'out' | 'both'; edgeType?: string }) =>
    withGraph(g => {
      if (!input?.id) return { status_code: 400 as const, body: { error: 'id is required' } }
      return neighbors(g, { id: input.id, direction: input.direction, edgeType: input.edgeType })
    }),
  { description: 'List nodes connected to a node, by edge direction and/or edge type' },
)

// --- understand::explain ----------------------------------------------------
iii.registerFunction(
  'understand::explain',
  async (input: { id?: string; file?: string }) =>
    withGraph(g => {
      if (!input?.id && !input?.file)
        return { status_code: 400 as const, body: { error: 'id or file is required' } }
      const result = explain(g, { id: input.id, file: input.file })
      return result ?? { status_code: 404 as const, body: { error: 'no matching node' } }
    }),
  { description: 'Deep-dive a file/node: summary plus what it depends on and what depends on it' },
)

// --- understand::tour -------------------------------------------------------
iii.registerFunction('understand::tour', async () => withGraph(g => tour(g)), {
  description: 'Guided, dependency-ordered tour steps for onboarding',
})

// --- HTTP triggers ----------------------------------------------------------
// Read-only GET surface mirroring the functions above.

iii.registerTrigger({
  type: 'http',
  function_id: 'understand::status',
  config: {
    api_path: '/understand/status',
    http_method: 'GET',
    description: 'Knowledge graph status',
  },
})

iii.registerTrigger({
  type: 'http',
  function_id: 'understand::overview',
  config: { api_path: '/understand/overview', http_method: 'GET', description: 'Project overview' },
})

// HTTP query/path params arrive as strings; adapt them into the function input.
iii.registerFunction(
  'understand::http::search',
  async (req: { query_params?: Record<string, string | string[]> }) => {
    const qp = req?.query_params ?? {}
    const limitRaw = firstParam(qp.limit)
    const result = withGraph(g =>
      search(g, {
        query: firstParam(qp.q) ?? firstParam(qp.query) ?? '',
        type: firstParam(qp.type),
        layer: firstParam(qp.layer),
        limit: limitRaw ? Number.parseInt(limitRaw, 10) : undefined,
      }),
    )
    return { status_code: 200, body: result }
  },
  { description: 'HTTP adapter for understand::search' },
)
iii.registerTrigger({
  type: 'http',
  function_id: 'understand::http::search',
  config: {
    api_path: '/understand/search',
    http_method: 'GET',
    description: 'Search graph nodes (?q=&type=&layer=&limit=)',
  },
})

iii.registerFunction(
  'understand::http::node',
  async (req: { path_params?: Record<string, string> }) => {
    const id = req?.path_params?.id
    const body = withGraph(g => {
      if (!id) return { error: 'id is required' }
      return getNode(g, id) ?? { error: `node not found: ${id}` }
    })
    return { status_code: 200, body }
  },
  { description: 'HTTP adapter for understand::node' },
)
iii.registerTrigger({
  type: 'http',
  function_id: 'understand::http::node',
  config: { api_path: '/understand/node/:id', http_method: 'GET', description: 'Get a node by id' },
})

iii.registerFunction(
  'understand::http::explain',
  async (req: {
    path_params?: Record<string, string>
    query_params?: Record<string, string | string[]>
  }) => {
    const id = req?.path_params?.id
    const file = firstParam(req?.query_params?.file)
    const body = withGraph(g => {
      if (!id && !file) return { error: 'id (path) or ?file= is required' }
      return explain(g, { id, file }) ?? { error: 'no matching node' }
    })
    return { status_code: 200, body }
  },
  { description: 'HTTP adapter for understand::explain' },
)
iii.registerTrigger({
  type: 'http',
  function_id: 'understand::http::explain',
  config: {
    api_path: '/understand/explain',
    http_method: 'GET',
    description: 'Explain a node (?file=) ',
  },
})

iii.registerTrigger({
  type: 'http',
  function_id: 'understand::tour',
  config: { api_path: '/understand/tour', http_method: 'GET', description: 'Guided tour steps' },
})

logger.info('understand worker registered', { graphPath: resolveGraphPath() })
