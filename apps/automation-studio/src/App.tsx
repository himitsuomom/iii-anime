import { useState } from 'react'
import { Assistant } from './components/Assistant.tsx'
import { Dashboard } from './components/Dashboard.tsx'
import { DescriptionGenerator } from './components/DescriptionGenerator.tsx'
import { Sidebar, type View } from './components/Sidebar.tsx'
import { TaskBoard } from './components/TaskBoard.tsx'

export function App() {
  const [view, setView] = useState<View>('dashboard')

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar view={view} onChange={setView} />
      <main className="flex-1 overflow-y-auto">
        {view === 'dashboard' && <Dashboard onNavigate={setView} />}
        {view === 'generator' && <DescriptionGenerator />}
        {view === 'assistant' && <Assistant />}
        {view === 'tasks' && <TaskBoard />}
      </main>
    </div>
  )
}
