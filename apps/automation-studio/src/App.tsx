import { useEffect, useState } from 'react'
import { Assistant } from './components/Assistant.tsx'
import { Dashboard } from './components/Dashboard.tsx'
import { DescriptionGenerator } from './components/DescriptionGenerator.tsx'
import { ProfitCalculator } from './components/ProfitCalculator.tsx'
import { Roadmap } from './components/Roadmap.tsx'
import { RoiSimulator } from './components/RoiSimulator.tsx'
import { Sidebar, type View } from './components/Sidebar.tsx'
import { TaskBoard } from './components/TaskBoard.tsx'
import { fetchHealth } from './lib/api.ts'

export function App() {
  const [view, setView] = useState<View>('dashboard')
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    fetchHealth()
      .then((h) => setOffline(!h.hasApiKey))
      .catch(() => setOffline(true))
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar view={view} onChange={setView} offline={offline} />
      <main className="flex-1 overflow-y-auto">
        {view === 'dashboard' && <Dashboard onNavigate={setView} />}
        {view === 'generator' && <DescriptionGenerator />}
        {view === 'assistant' && <Assistant />}
        {view === 'profit' && <ProfitCalculator />}
        {view === 'roi' && <RoiSimulator />}
        {view === 'roadmap' && <Roadmap />}
        {view === 'tasks' && <TaskBoard />}
      </main>
    </div>
  )
}
