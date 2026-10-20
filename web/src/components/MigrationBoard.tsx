import React, { useState } from 'react'
import type { TableRow } from '../types'

interface MigrationBoardProps {
  tables: TableRow[]
  onSelectTable: (table: TableRow) => void
  onStartNewRun: () => void
}

export const MigrationBoard: React.FC<MigrationBoardProps> = ({
  tables,
  onSelectTable,
  onStartNewRun,
}) => {
  const [filter, setFilter] = useState<string>('ALL')
  const [copiedThreadId, setCopiedThreadId] = useState<string | null>(null)

  const handleCopyThread = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    navigator.clipboard.writeText(threadId)
    setCopiedThreadId(threadId)
    setTimeout(() => setCopiedThreadId(null), 2000)
  }

  const filteredTables = tables.filter((t) => {
    if (filter === 'ALL') return true
    if (filter === 'NEEDS REVIEW') return t.status.includes('NEEDS REVIEW')
    if (filter === 'FIXING') return t.status.includes('FIXING')
    if (filter === 'PROMOTED') return t.status === 'PROMOTED'
    if (filter === 'BLOCKED') return t.status.includes('BLOCKED')
    if (filter === 'QUEUED') return t.status === 'QUEUED'
    return true
  })

  const getStatusBadge = (status: string, hasPii: boolean, piiCount: number) => {
    if (status === 'PROMOTED') {
      return <span className="badge badge-green">PROMOTED</span>
    }
    if (status.includes('NEEDS REVIEW')) {
      return (
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span className="badge badge-inverted">NEEDS REVIEW</span>
          {hasPii && <span className="badge badge-amber">PII {piiCount}</span>}
        </div>
      )
    }
    if (status.includes('FIXING')) {
      return <span className="badge badge-amber pulse-running">FIXING</span>
    }
    if (status.includes('BLOCKED')) {
      return <span className="badge" style={{ color: 'var(--text-disabled)', borderColor: 'var(--border)' }}>{status}</span>
    }
    if (status === 'QUEUED') {
      return <span className="badge" style={{ color: 'var(--text-secondary)' }}>QUEUED</span>
    }
    return <span className="badge">{status}</span>
  }

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Board Controls Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="label-mono" style={{ marginRight: '8px' }}>FILTER:</span>
          {['ALL', 'NEEDS REVIEW', 'FIXING', 'PROMOTED', 'BLOCKED', 'QUEUED'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                background: filter === f ? 'var(--text-display)' : 'transparent',
                color: filter === f ? 'var(--black)' : 'var(--text-secondary)',
                border: '1px solid var(--border-visible)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                padding: '4px 10px',
                cursor: 'pointer',
                fontWeight: filter === f ? 700 : 400,
              }}
            >
              {f}
            </button>
          ))}
        </div>

        <button className="btn-pill btn-secondary" onClick={onStartNewRun}>
          + START RUN
        </button>
      </div>

      {/* Main Table Grid */}
      <div
        style={{
          border: '1px solid var(--border-visible)',
          backgroundColor: 'var(--surface)',
          overflowX: 'auto',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-visible)' }}>
              <th className="label-mono" style={{ padding: '12px 16px', width: '48px' }}>#</th>
              <th className="label-mono" style={{ padding: '12px 16px' }}>TABLE</th>
              <th className="label-mono" style={{ padding: '12px 16px' }}>DEPENDS ON</th>
              <th className="label-mono" style={{ padding: '12px 16px' }}>CHECKS</th>
              <th className="label-mono" style={{ padding: '12px 16px' }}>ATTEMPTS</th>
              <th className="label-mono" style={{ padding: '12px 16px' }}>STATUS</th>
              <th className="label-mono" style={{ padding: '12px 16px', textAlign: 'right' }}>THREAD ID</th>
            </tr>
          </thead>
          <tbody>
            {filteredTables.map((t) => (
              <tr
                key={t.table_name}
                onClick={() => onSelectTable(t)}
                style={{
                  borderBottom: '1px solid var(--border)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease-out',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--surface-raised)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-disabled)' }}>
                  {t.table_num}
                </td>
                <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-display)' }}>
                  {t.table_name}
                </td>
                <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {t.depends_on}
                </td>
                <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  {t.checks}
                </td>
                <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {t.attempts}
                </td>
                <td style={{ padding: '14px 16px' }}>
                  {getStatusBadge(t.status, t.has_pii, t.pii_count)}
                </td>
                <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                  <button
                    onClick={(e) => handleCopyThread(e, t.thread_id)}
                    title="Copy Thread ID"
                    style={{
                      background: 'transparent',
                      border: '1px solid var(--border)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                      color: copiedThreadId === t.thread_id ? 'var(--success-green)' : 'var(--text-disabled)',
                      padding: '2px 8px',
                      cursor: 'pointer',
                    }}
                  >
                    {copiedThreadId === t.thread_id ? 'COPIED' : `⎘ ${t.thread_id}`}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
