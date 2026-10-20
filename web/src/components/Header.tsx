import React from 'react'
import type { RunSummary } from '../types'

interface HeaderProps {
  runId: string
  targetEnv: string
  modelName: string
  summary: RunSummary
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  onSelectFixture: (fixtureName: string) => void
  onGoHome: () => void
}

export const Header: React.FC<HeaderProps> = ({
  runId,
  targetEnv,
  modelName,
  summary,
  theme,
  onToggleTheme,
  onSelectFixture,
  onGoHome,
}) => {
  return (
    <header
      style={{
        borderBottom: '1px solid var(--border-visible)',
        backgroundColor: 'var(--surface)',
        padding: '14px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      {/* Top telemetry bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={onGoHome}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: '16px',
              color: 'var(--text-display)',
              letterSpacing: '-0.01em',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>LEGACY // LAKEHOUSE</span>
          </button>
          <span className="badge badge-inverted">OPERATOR CONSOLE v2</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          {/* Permanent Target Environment Badge (Principle 6 in ui-2.md) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span className="label-mono">TARGET ENVIRONMENT</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700, color: 'var(--text-display)' }}>
              {targetEnv}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span className="label-mono">INFERENCE MODEL</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)' }}>
              {modelName}
            </span>
          </div>

          {/* Fixture preview selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span className="label-mono">INSPECT STATE</span>
            <select
              onChange={(e) => onSelectFixture(e.target.value)}
              style={{
                backgroundColor: 'var(--surface-raised)',
                border: '1px solid var(--border-visible)',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                padding: '4px 8px',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="live">LIVE: {runId.toUpperCase()}</option>
              <option value="passed">FIXTURE: PASSED FIRST TIME</option>
              <option value="mid_repair">FIXTURE: MID-REPAIR (ATTEMPT 2)</option>
              <option value="failed_closed">FIXTURE: FAILED CLOSED (ATTEMPT 3)</option>
            </select>
          </div>

          {/* Theme switcher */}
          <div style={{ display: 'inline-flex', border: '1px solid var(--border-visible)' }}>
            <button
              onClick={onToggleTheme}
              className={`label-mono`}
              style={{
                background: theme === 'dark' ? 'var(--text-display)' : 'transparent',
                color: theme === 'dark' ? 'var(--black)' : 'var(--text-secondary)',
                border: 'none',
                padding: '6px 12px',
                cursor: 'pointer',
                fontWeight: theme === 'dark' ? 700 : 400,
              }}
            >
              DARK
            </button>
            <button
              onClick={onToggleTheme}
              className={`label-mono`}
              style={{
                background: theme === 'light' ? 'var(--text-display)' : 'transparent',
                color: theme === 'light' ? 'var(--black)' : 'var(--text-secondary)',
                border: 'none',
                padding: '6px 12px',
                cursor: 'pointer',
                fontWeight: theme === 'light' ? 700 : 400,
              }}
            >
              LIGHT
            </button>
          </div>
        </div>
      </div>

      {/* Summary strip with single Hero Counter per ui-2.md */}
      <div
        style={{
          borderTop: '1px solid var(--border)',
          paddingTop: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: 'var(--text-display)' }}>
            {runId.toUpperCase()}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
            {summary.total_tables} TABLES
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)' }}>
            {summary.promoted} PROMOTED · {summary.needs_review} NEEDS REVIEW · {summary.fixing} FIXING · {summary.blocked} BLOCKED
          </span>
        </div>

        <div>
          <span className="hero-counter">{summary.display_counter}</span>
        </div>
      </div>
    </header>
  )
}
