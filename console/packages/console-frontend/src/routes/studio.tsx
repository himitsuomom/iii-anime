import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import {
  approveProject,
  askWiki,
  createProject,
  listProjects,
  listWiki,
  rejectProject,
  type ProjectSummary,
} from '@/api/studio'

export const Route = createFileRoute('/studio')({
  component: StudioPage,
})

const STATUS_STYLES: Record<string, string> = {
  delivered: 'bg-green-500/15 text-green-400',
  failed: 'bg-red-500/15 text-red-400',
  awaiting_approval: 'bg-amber-500/15 text-amber-400',
}

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? 'bg-accent/15 text-accent'
  return <span className={`text-[11px] px-2 py-0.5 rounded-full ${cls}`}>{status}</span>
}

function ProjectCard({ p, onAct }: { p: ProjectSummary; onAct: (id: string, a: 'approve' | 'reject') => void }) {
  const awaiting = p.status === 'awaiting_approval'
  return (
    <div className="border border-border-subtle rounded-[var(--radius-lg)] p-3 mb-2">
      <div className="flex items-center justify-between gap-2">
        <StatusBadge status={p.status} />
        <span className="text-xs text-secondary font-mono">{p.project_id}</span>
      </div>
      <div className="mt-1 text-sm">{p.goal ?? '(working…)'}</div>
      <div className="text-xs text-secondary mt-1">
        {p.app_type ?? '—'} · iter {p.iteration}
        {p.passed === true ? ' · QA ✓' : p.passed === false ? ' · QA ✗' : ''}
      </div>
      {awaiting && (
        <div className="flex gap-2 mt-2">
          <button
            type="button"
            className="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400"
            onClick={() => onAct(p.project_id, 'approve')}
          >
            approve
          </button>
          <button
            type="button"
            className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400"
            onClick={() => onAct(p.project_id, 'reject')}
          >
            reject
          </button>
        </div>
      )}
    </div>
  )
}

function StudioPage() {
  const qc = useQueryClient()
  const [idea, setIdea] = useState('')
  const [approval, setApproval] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)

  const projects = useQuery({
    queryKey: ['studio', 'projects'],
    queryFn: listProjects,
    refetchInterval: 3000,
  })
  const wiki = useQuery({ queryKey: ['studio', 'wiki'], queryFn: listWiki, refetchInterval: 8000 })

  const submit = useMutation({
    mutationFn: () => createProject(idea.trim(), approval),
    onSuccess: () => {
      setIdea('')
      qc.invalidateQueries({ queryKey: ['studio', 'projects'] })
    },
  })
  const act = useMutation({
    mutationFn: ({ id, a }: { id: string; a: 'approve' | 'reject' }) =>
      a === 'approve' ? approveProject(id) : rejectProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['studio', 'projects'] }),
  })
  const ask = useMutation({
    mutationFn: () => askWiki(question.trim()),
    onSuccess: (r) =>
      setAnswer(r.answer + (r.sources?.length ? `\n\nsources: ${r.sources.join(', ')}` : '')),
  })

  const list = projects.data?.projects ?? []
  const pages = wiki.data?.pages ?? []

  return (
    <div className="p-4 md:p-6 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
      <div>
        <h1 className="text-lg font-sans font-medium mb-3">App Studio</h1>
        <div className="border border-border-subtle rounded-[var(--radius-lg)] p-3 mb-4">
          <textarea
            className="w-full bg-background border border-border-subtle rounded p-2 text-sm"
            rows={2}
            placeholder="Describe an app idea…"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
          />
          <div className="flex items-center gap-3 mt-2">
            <button
              type="button"
              className="text-sm px-3 py-1.5 rounded bg-accent text-background font-medium disabled:opacity-50"
              disabled={!idea.trim() || submit.isPending}
              onClick={() => submit.mutate()}
            >
              Build it
            </button>
            <label className="text-xs text-secondary flex items-center gap-1.5">
              <input type="checkbox" checked={approval} onChange={(e) => setApproval(e.target.checked)} />
              require approval
            </label>
          </div>
        </div>

        {projects.isError ? (
          <p className="text-sm text-red-400">
            Can't reach the studio. Is the app-studio worker running on this engine? (set
            VITE_STUDIO_BASE to point elsewhere)
          </p>
        ) : list.length === 0 ? (
          <p className="text-sm text-secondary italic">No projects yet.</p>
        ) : (
          list.map((p) => (
            <ProjectCard key={p.project_id} p={p} onAct={(id, a) => act.mutate({ id, a })} />
          ))
        )}
      </div>

      <aside>
        <div className="border border-border-subtle rounded-[var(--radius-lg)] p-3 mb-4">
          <h2 className="text-xs uppercase tracking-wide text-secondary mb-2">Ask the wiki</h2>
          <input
            type="text"
            className="w-full bg-background border border-border-subtle rounded p-2 text-sm"
            placeholder="which apps expose /health?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="button"
            className="text-sm px-3 py-1.5 mt-2 rounded bg-elevated border border-border-subtle disabled:opacity-50"
            disabled={!question.trim() || ask.isPending}
            onClick={() => ask.mutate()}
          >
            {ask.isPending ? 'thinking…' : 'Ask'}
          </button>
          {answer && (
            <pre className="mt-2 text-xs whitespace-pre-wrap bg-background border border-border-subtle rounded p-2">
              {answer}
            </pre>
          )}
        </div>
        <div className="border border-border-subtle rounded-[var(--radius-lg)] p-3">
          <h2 className="text-xs uppercase tracking-wide text-secondary mb-2">Wiki pages</h2>
          {pages.length === 0 ? (
            <p className="text-sm text-secondary italic">No pages yet.</p>
          ) : (
            pages.map((p) => (
              <div key={p.slug} className="border border-border-subtle rounded p-2 mb-2">
                <div className="text-sm">{p.title}</div>
                <div className="text-xs text-secondary font-mono">{p.slug}</div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  )
}
