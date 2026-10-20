import React, { useEffect, useState } from 'react'
import { Header } from './components/Header'
import { MigrationBoard } from './components/MigrationBoard'
import { TableReview } from './components/TableReview'
import type { BoardData, TableReviewState, TableRow } from './types'

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [currentView, setCurrentView] = useState<'board' | 'review'>('board')
  const [boardData, setBoardData] = useState<BoardData | null>(null)
  const [reviewState, setReviewState] = useState<TableReviewState | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  // Toggle Theme
  const handleToggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(nextTheme)
    document.documentElement.setAttribute('data-theme', nextTheme)
  }

  // Load Board Data
  const fetchBoard = async () => {
    try {
      const res = await fetch('/api/runs/run_07')
      if (res.ok) {
        const data = await res.json()
        setBoardData(data)
      }
    } catch (err) {
      console.error('Failed to load board data:', err)
    } finally {
      setLoading(false)
    }
  }

  // Load Review State for a thread
  const loadThreadState = async (threadId: string) => {
    try {
      setLoading(true)
      const res = await fetch(`/api/threads/${threadId}/state`)
      if (res.ok) {
        const data = await res.json()
        setReviewState(data)
        setCurrentView('review')
      }
    } catch (err) {
      console.error('Failed to load thread review state:', err)
    } finally {
      setLoading(false)
    }
  }

  // Select Fixture
  const handleSelectFixture = async (fixtureName: string) => {
    if (fixtureName === 'live') {
      fetchBoard()
      setCurrentView('board')
      return
    }

    try {
      setLoading(true)
      const res = await fetch(`/api/fixtures/${fixtureName}`)
      if (res.ok) {
        const data = await res.json()
        setReviewState(data)
        setCurrentView('review')
      }
    } catch (err) {
      console.error('Failed to load fixture:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBoard()

    // Connect to SSE event stream
    const eventSource = new EventSource('/api/runs/run_07/events')
    eventSource.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data)
        if (evt.type === 'NODE_EVENT') {
          // Refresh board when node events complete
          fetchBoard()
        }
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    return () => {
      eventSource.close()
    }
  }, [])

  const handleSelectTable = (table: TableRow) => {
    loadThreadState(table.thread_id)
  }

  const handleApprove = async () => {
    if (!reviewState) return
    try {
      setLoading(true)
      const res = await fetch(`/api/threads/${reviewState.thread_id}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve' }),
      })
      if (res.ok) {
        const data = await res.json()
        setReviewState(data.state)
        fetchBoard()
      }
    } catch (err) {
      console.error('Approval failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRequestChanges = async (target: string, feedback: string) => {
    if (!reviewState) return
    try {
      setLoading(true)
      const res = await fetch(`/api/threads/${reviewState.thread_id}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'changes',
          feedback: `[Target: ${target}] ${feedback}`,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setReviewState(data.state)
        fetchBoard()
      }
    } catch (err) {
      console.error('Request changes failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAbort = async () => {
    if (!reviewState) return
    try {
      setLoading(true)
      const res = await fetch(`/api/threads/${reviewState.thread_id}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'abort' }),
      })
      if (res.ok) {
        const data = await res.json()
        setReviewState(data.state)
        fetchBoard()
      }
    } catch (err) {
      console.error('Abort failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateTreatment = (sourceCol: string, newTreatment: 'hash' | 'mask' | 'keep' | 'drop') => {
    if (!reviewState) return
    const updated = {
      ...reviewState,
      column_treatments: reviewState.column_treatments.map((c) =>
        c.source_col === sourceCol ? { ...c, treatment: newTreatment } : c
      ),
    }
    setReviewState(updated)
  }

  const handleExportDiagnostics = () => {
    if (!reviewState) return
    const blob = new Blob([JSON.stringify(reviewState, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `diagnostics_${reviewState.current_table}.json`
    a.click()
  }

  const handleStartNewRun = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'LOCAL · DUCKDB', provider: 'ollama' }),
      })
      if (res.ok) {
        fetchBoard()
      }
    } catch (err) {
      console.error('Failed to start run:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading && !boardData && !reviewState) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
        <span className="label-mono">[INITIALIZING OPERATOR CONSOLE...]</span>
      </div>
    )
  }

  const summary = boardData?.summary || {
    total_tables: 6,
    promoted: 2,
    needs_review: 2,
    fixing: 1,
    blocked: 1,
    display_counter: '2/6 PROMOTED',
  }

  return (
    <div className="dot-grid" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        runId={boardData?.run_id || 'run_07'}
        targetEnv={boardData?.target_environment || 'LOCAL · DUCKDB'}
        modelName={boardData?.model_name || 'llama3.2 (ollama)'}
        summary={summary}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        onSelectFixture={handleSelectFixture}
        onGoHome={() => setCurrentView('board')}
      />

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {currentView === 'board' && boardData && (
          <MigrationBoard
            tables={boardData.tables}
            onSelectTable={handleSelectTable}
            onStartNewRun={handleStartNewRun}
          />
        )}

        {currentView === 'review' && reviewState && (
          <TableReview
            state={reviewState}
            onBackToBoard={() => setCurrentView('board')}
            onApprove={handleApprove}
            onRequestChanges={handleRequestChanges}
            onAbort={handleAbort}
            onUpdateTreatment={handleUpdateTreatment}
            onExportDiagnostics={handleExportDiagnostics}
          />
        )}
      </main>
    </div>
  )
}

export default App
