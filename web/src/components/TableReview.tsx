import React, { useState } from 'react'
import type { TableReviewState } from '../types'

interface TableReviewProps {
  state: TableReviewState
  onBackToBoard: () => void
  onApprove: () => void
  onRequestChanges: (target: string, feedback: string) => void
  onAbort: () => void
  onUpdateTreatment: (sourceCol: string, newTreatment: 'hash' | 'mask' | 'keep' | 'drop') => void
  onExportDiagnostics: () => void
}

export const TableReview: React.FC<TableReviewProps> = ({
  state,
  onBackToBoard,
  onApprove,
  onRequestChanges,
  onAbort,
  onUpdateTreatment,
  onExportDiagnostics,
}) => {
  const [activeTab, setActiveTab] = useState<'checks' | 'pii' | 'code' | 'attempts'>('checks')
  const [reviewedSensitive, setReviewedSensitive] = useState<boolean>(false)
  const [showChangesModal, setShowChangesModal] = useState<boolean>(false)
  const [showAbortModal, setShowAbortModal] = useState<boolean>(false)
  const [changeTarget, setChangeTarget] = useState<string>('general')
  const [changeComment, setChangeComment] = useState<string>('')
  const [traceExpanded, setTraceExpanded] = useState<boolean>(false)
  const [expandedPromptIdx, setExpandedPromptIdx] = useState<number | null>(null)

  const sensitiveCols = state.column_treatments.filter((c) => c.is_sensitive)
  const sensitiveCount = sensitiveCols.length

  // Checks calculations
  const totalChecks = state.checks.length
  const passedChecks = state.checks.filter((c) => c.status === 'PASS').length
  const failedChecks = state.checks.filter((c) => c.status === 'FAIL')
  const hasFailing = failedChecks.length > 0

  // Worst-case headline
  const headline = hasFailing
    ? `${passedChecks} of ${totalChecks} pass, ${failedChecks.length} failing (${failedChecks[0].name})`
    : `${totalChecks} of ${totalChecks} checks pass`

  // Can approve?
  const canApprove =
    state.status !== 'FAILED_CLOSED' &&
    state.status !== 'ABORTED' &&
    !hasFailing &&
    (sensitiveCount === 0 || reviewedSensitive)

  const remainingRetries = Math.max(0, state.max_retries - state.fix_attempts)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 120px)' }}>
      {/* Sub-header / Breadcrumb */}
      <div
        style={{
          borderBottom: '1px solid var(--border-visible)',
          backgroundColor: 'var(--surface)',
          padding: '12px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={onBackToBoard}
            className="btn-pill btn-secondary"
            style={{ padding: '6px 14px', minHeight: '32px', fontSize: '11px' }}
          >
            &lt; BOARD
          </button>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700, color: 'var(--text-display)' }}>
            {state.current_table}
          </span>
          <span className="badge">{state.run_id.toUpperCase()}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="label-mono">TARGET:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700 }}>
            {state.target_environment}
          </span>
        </div>
      </div>

      {/* Main Split: Evidence Left, Decision Rail Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', flex: 1 }}>
        
        {/* LEFT PANE: EVIDENCE TABS */}
        <div
          style={{
            borderRight: '1px solid var(--border-visible)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Tab Strip */}
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid var(--border-visible)',
              backgroundColor: 'var(--surface-raised)',
            }}
          >
            <button
              onClick={() => setActiveTab('checks')}
              className="label-mono"
              style={{
                background: activeTab === 'checks' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'checks' ? 'var(--text-display)' : 'var(--text-secondary)',
                border: 'none',
                borderRight: '1px solid var(--border-visible)',
                borderBottom: activeTab === 'checks' ? '2px solid var(--text-display)' : 'none',
                padding: '14px 20px',
                cursor: 'pointer',
                fontWeight: activeTab === 'checks' ? 700 : 400,
              }}
            >
              CHECKS ({passedChecks}/{totalChecks})
            </button>
            <button
              onClick={() => setActiveTab('pii')}
              className="label-mono"
              style={{
                background: activeTab === 'pii' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'pii' ? 'var(--text-display)' : 'var(--text-secondary)',
                border: 'none',
                borderRight: '1px solid var(--border-visible)',
                borderBottom: activeTab === 'pii' ? '2px solid var(--text-display)' : 'none',
                padding: '14px 20px',
                cursor: 'pointer',
                fontWeight: activeTab === 'pii' ? 700 : 400,
              }}
            >
              SCHEMA & PII {sensitiveCount > 0 ? `(${sensitiveCount})` : ''}
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className="label-mono"
              style={{
                background: activeTab === 'code' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'code' ? 'var(--text-display)' : 'var(--text-secondary)',
                border: 'none',
                borderRight: '1px solid var(--border-visible)',
                borderBottom: activeTab === 'code' ? '2px solid var(--text-display)' : 'none',
                padding: '14px 20px',
                cursor: 'pointer',
                fontWeight: activeTab === 'code' ? 700 : 400,
              }}
            >
              CODE
            </button>
            <button
              onClick={() => setActiveTab('attempts')}
              className="label-mono"
              style={{
                background: activeTab === 'attempts' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'attempts' ? 'var(--text-display)' : 'var(--text-secondary)',
                border: 'none',
                borderRight: '1px solid var(--border-visible)',
                borderBottom: activeTab === 'attempts' ? '2px solid var(--text-display)' : 'none',
                padding: '14px 20px',
                cursor: 'pointer',
                fontWeight: activeTab === 'attempts' ? 700 : 400,
              }}
            >
              ATTEMPTS ({state.attempts.length})
            </button>
          </div>

          {/* TAB 1: CHECKS */}
          {activeTab === 'checks' && (
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <span className="label-mono">WORST-CASE PARITY READOUT</span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px', marginTop: '4px' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '20px',
                      fontWeight: 700,
                      color: hasFailing ? 'var(--accent-red)' : 'var(--text-display)',
                    }}
                  >
                    {headline}
                  </span>
                </div>
              </div>

              {/* Segmented bar: EXACTLY ONE SEGMENT PER CHECK per ui-2.md */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span className="label-mono">DISCRETE RECONCILIATION SEGMENTS</span>
                <div style={{ display: 'flex', gap: '3px', height: '14px', width: '100%' }}>
                  {state.checks.map((chk, idx) => (
                    <div
                      key={idx}
                      title={`${chk.name}: ${chk.status}`}
                      style={{
                        flex: 1,
                        backgroundColor:
                          chk.status === 'PASS'
                            ? 'var(--text-display)'
                            : 'var(--accent-red)',
                        height: '100%',
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Checks Table */}
              <div style={{ border: '1px solid var(--border-visible)', backgroundColor: 'var(--surface)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-visible)' }}>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>CHECK</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>SOURCE</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>TARGET</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>TOL</th>
                      <th className="label-mono" style={{ padding: '10px 16px', textAlign: 'right' }}>RESULT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.checks.map((c, i) => (
                      <tr
                        key={i}
                        style={{
                          borderBottom: '1px solid var(--border)',
                          backgroundColor: c.status === 'FAIL' ? 'var(--accent-subtle)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-display)' }}>
                            {c.name}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                            {c.description}
                          </div>
                          {c.error_message && (
                            <div style={{ fontSize: '11px', color: 'var(--accent-red)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                              [ERROR: {c.error_message}]
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                          {String(c.source_value ?? '-')}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                          {String(c.target_value ?? '-')}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          {c.tolerance}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          {c.status === 'PASS' ? (
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--success-green)' }}>
                              PASS
                            </span>
                          ) : (
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-red)' }}>
                              FAIL
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: SCHEMA & PII */}
          {activeTab === 'pii' && (
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="label-mono">SOURCE TO LAKEHOUSE TARGET MAPPING & SENSITIVITY GOVERNANCE</span>
                <span className="label-mono">SAFE SAMPLE AUDIT (BOTH SIDES MASKED)</span>
              </div>

              <div style={{ border: '1px solid var(--border-visible)', backgroundColor: 'var(--surface)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-visible)' }}>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>SOURCE COLUMN</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>TARGET COLUMN</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>TYPE CHANGE</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>SENSITIVITY</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>TREATMENT</th>
                      <th className="label-mono" style={{ padding: '10px 16px' }}>SAMPLES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.column_treatments.map((col, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', color: 'var(--text-display)' }}>
                          {col.source_col}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-display)' }}>
                          {col.target_col}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                          {col.source_type} &rarr; {col.target_type}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          {col.is_sensitive ? (
                            <span className="badge badge-amber">{col.sensitivity_type || 'PII'}</span>
                          ) : (
                            <span style={{ color: 'var(--text-disabled)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>-</span>
                          )}
                          {col.ai_suggested && (
                            <span className="badge" style={{ marginLeft: '4px', fontSize: '9px' }}>AI-SUGGESTED</span>
                          )}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <select
                            value={col.treatment}
                            onChange={(e) =>
                              onUpdateTreatment(col.source_col, e.target.value as 'hash' | 'mask' | 'keep' | 'drop')
                            }
                            style={{
                              backgroundColor: 'var(--surface-raised)',
                              border: '1px solid var(--border-visible)',
                              color: 'var(--text-primary)',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '11px',
                              padding: '4px 6px',
                              outline: 'none',
                              cursor: 'pointer',
                            }}
                          >
                            <option value="hash">hash</option>
                            <option value="mask">mask</option>
                            <option value="keep">keep</option>
                            <option value="drop">drop</option>
                          </select>
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                          <div>pre: {col.sample_before.join(', ')}</div>
                          <div style={{ color: 'var(--text-primary)' }}>post: {col.sample_after.join(', ')}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: CODE */}
          {activeTab === 'code' && (
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="label-mono">SIDE-BY-SIDE TRANSFORMATION STATEMENTS & PROVENANCE</span>
                <span className="label-mono">TAGGED: [RULE: SQLGLOT] VS [MODEL: LLM]</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {state.provenance.map((stmt, i) => (
                  <div
                    key={i}
                    style={{
                      border: '1px solid var(--border-visible)',
                      backgroundColor: 'var(--surface)',
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 90px',
                      gap: '16px',
                      padding: '16px',
                    }}
                  >
                    <div>
                      <div className="label-mono" style={{ marginBottom: '6px' }}>LEGACY SOURCE SQL</div>
                      <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>
                        {stmt.statement_sql}
                      </pre>
                    </div>

                    <div>
                      <div className="label-mono" style={{ marginBottom: '6px' }}>GENERATED PYSPARK</div>
                      <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
                        {stmt.pyspark_equivalent}
                      </pre>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end' }}>
                      <span className={`badge ${stmt.provenance === 'RULE' ? '' : 'badge-inverted'}`}>
                        {stmt.provenance}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: ATTEMPTS */}
          {activeTab === 'attempts' && (
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <span className="label-mono">REPAIR ATTEMPTS & DIAGNOSTIC TIMELINE</span>

              {state.attempts.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', border: '1px solid var(--border)', backgroundColor: 'var(--surface)' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-primary)' }}>
                    Passed first time (0 repair cycles required)
                  </span>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {state.attempts.map((att, i) => (
                    <div
                      key={i}
                      style={{
                        border: '1px solid var(--border-visible)',
                        backgroundColor: 'var(--surface)',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-display)' }}>
                          ATTEMPT {att.attempt_number}
                        </span>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span className="badge badge-red">{att.result_status}</span>
                          <span className="label-mono">{att.timestamp}</span>
                        </div>
                      </div>

                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        <strong>Diagnosis:</strong> {att.diagnosis}
                      </div>

                      <div style={{ backgroundColor: 'var(--black)', padding: '12px', border: '1px solid var(--border)' }}>
                        <div className="label-mono" style={{ marginBottom: '6px' }}>PATCH DIFF</div>
                        <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                          {att.patch_diff}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT PANE: DECISION RAIL (ALWAYS VISIBLE per ui-2.md) */}
        <div
          style={{
            backgroundColor: 'var(--surface)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}
        >
          {/* Status Section */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span className="label-mono">OPERATOR DECISION STATUS</span>
            <div>
              {state.status === 'PROMOTED' ? (
                <span className="badge badge-green" style={{ fontSize: '13px', padding: '6px 12px' }}>PROMOTED</span>
              ) : state.status === 'FAILED_CLOSED' ? (
                <span className="badge badge-red" style={{ fontSize: '13px', padding: '6px 12px' }}>FAILED CLOSED</span>
              ) : (
                <span className="badge badge-inverted" style={{ fontSize: '13px', padding: '6px 12px' }}>NEEDS REVIEW</span>
              )}
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {state.repair_summary}
            </span>
          </div>

          {/* Sensitive Columns Confirmation Checkbox (Requirement in ui-2.md) */}
          {sensitiveCount > 0 && state.status !== 'PROMOTED' && (
            <div
              style={{
                border: '1px solid var(--border-visible)',
                padding: '14px',
                backgroundColor: 'var(--surface-raised)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={reviewedSensitive}
                  onChange={(e) => setReviewedSensitive(e.target.checked)}
                  style={{ accentColor: 'var(--text-display)', width: '16px', height: '16px', cursor: 'pointer' }}
                />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-display)', fontWeight: 700 }}>
                  I reviewed {sensitiveCount} sensitive columns
                </span>
              </label>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Approve unlocks only after explicit confirmation of PII treatments.
              </span>
            </div>
          )}

          {/* Primary Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {state.status !== 'FAILED_CLOSED' && state.status !== 'PROMOTED' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <button
                  disabled={!canApprove}
                  onClick={onApprove}
                  className="btn-pill btn-primary"
                  style={{ width: '100%' }}
                >
                  [ APPROVE ]
                </button>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                  Promotes {state.staging_entity} to {state.target_entity}, writes tags
                </span>
              </div>
            )}

            {state.status !== 'PROMOTED' && (
              <button
                onClick={() => setShowChangesModal(true)}
                className="btn-pill btn-secondary"
                style={{ width: '100%' }}
              >
                [ REQUEST CHANGES ]
              </button>
            )}

            {state.status === 'FAILED_CLOSED' && (
              <button
                onClick={onExportDiagnostics}
                className="btn-pill btn-secondary"
                style={{ width: '100%' }}
              >
                [ EXPORT DIAGNOSTICS ]
              </button>
            )}

            {state.status !== 'PROMOTED' && (
              <button
                onClick={() => setShowAbortModal(true)}
                className="btn-pill btn-destructive"
                style={{ width: '100%' }}
              >
                [ ABORT ]
              </button>
            )}
          </div>

          {/* Remaining retry budget indicator */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
            <span className="label-mono">RETRY BUDGET:</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)', marginTop: '4px' }}>
              {remainingRetries} of {state.max_retries} attempts remaining
            </div>
          </div>
        </div>
      </div>

      {/* DEVELOPER RUN TRACE DRAWER (COLLAPSED BY DEFAULT per ui-2.md) */}
      <div
        style={{
          borderTop: '1px solid var(--border-visible)',
          backgroundColor: 'var(--surface)',
        }}
      >
        <button
          onClick={() => setTraceExpanded(!traceExpanded)}
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            padding: '12px 24px',
            textAlign: 'left',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            fontWeight: 700,
            color: 'var(--text-display)',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{traceExpanded ? 'v' : '>'} RUN TRACE (developer)</span>
          <span className="label-mono">NODES, TOKENS & LATENCY</span>
        </button>

        {traceExpanded && (
          <div
            style={{
              padding: '20px 24px',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              backgroundColor: 'var(--black)',
            }}
          >
            {/* Real Graph Topology */}
            <div>
              <span className="label-mono">EXECUTION TOPOLOGY & NODE STATUS</span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                {state.graph_nodes.map((n) => (
                  <div
                    key={n.id}
                    style={{
                      border: `1px solid ${
                        n.status === 'HALTED'
                          ? 'var(--accent-red)'
                          : n.status === 'COMPLETED'
                          ? 'var(--border-visible)'
                          : 'var(--border)'
                      }`,
                      backgroundColor: 'var(--surface)',
                      padding: '8px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '2px',
                    }}
                  >
                    <span className="label-mono">{n.label}</span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color:
                          n.status === 'HALTED'
                            ? 'var(--accent-red)'
                            : n.status === 'COMPLETED'
                            ? 'var(--success-green)'
                            : 'var(--text-disabled)',
                      }}
                    >
                      {n.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Per-node Duration & Tokens */}
            <div>
              <span className="label-mono">PER-NODE TELEMETRY & TOKEN COUNTS</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                {state.telemetry.map((t, idx) => (
                  <div
                    key={idx}
                    style={{
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--surface)',
                      padding: '10px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-display)' }}>
                        {t.node_name.toUpperCase()} · {t.model_name}
                      </span>
                      <div style={{ display: 'flex', gap: '16px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                        <span>{t.duration_ms.toFixed(1)}ms</span>
                        <span>in: {t.tokens_input} tok</span>
                        <span>out: {t.tokens_output} tok</span>
                        {t.prompt && (
                          <button
                            onClick={() => setExpandedPromptIdx(expandedPromptIdx === idx ? null : idx)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--interactive-blue)',
                              cursor: 'pointer',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {expandedPromptIdx === idx ? '[HIDE PROMPT]' : '[VIEW PROMPT]'}
                          </button>
                        )}
                      </div>
                    </div>

                    {expandedPromptIdx === idx && t.prompt && (
                      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
                        <div className="label-mono">LLM PROMPT</div>
                        <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                          {t.prompt}
                        </pre>
                        <div className="label-mono" style={{ marginTop: '8px' }}>LLM RESPONSE</div>
                        <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                          {t.response}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* REQUEST CHANGES MODAL */}
      {showChangesModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border-visible)',
              padding: '24px',
              maxWidth: '480px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: 'var(--text-display)' }}>
                REQUEST CHANGES (SPENDS 1 RETRY)
              </span>
              <button
                onClick={() => setShowChangesModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                [ X ]
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span className="label-mono">TARGET</span>
              <select
                value={changeTarget}
                onChange={(e) => setChangeTarget(e.target.value)}
                style={{
                  backgroundColor: 'var(--surface-raised)',
                  border: '1px solid var(--border-visible)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  padding: '8px',
                  outline: 'none',
                }}
              >
                <option value="general">General instruction</option>
                {state.checks.map((c) => (
                  <option key={c.name} value={`check:${c.name}`}>Check: {c.name}</option>
                ))}
                {state.column_treatments.map((col) => (
                  <option key={col.source_col} value={`col:${col.source_col}`}>Column: {col.source_col}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span className="label-mono">COMMENT & CORRECTION INSTRUCTION</span>
              <textarea
                rows={3}
                value={changeComment}
                onChange={(e) => setChangeComment(e.target.value)}
                placeholder="e.g. Enforce secondary order by order_id asc to break window tie-breaker..."
                style={{
                  backgroundColor: 'var(--surface-raised)',
                  border: '1px solid var(--border-visible)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  padding: '8px',
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <button className="btn-pill btn-secondary" onClick={() => setShowChangesModal(false)}>
                CANCEL
              </button>
              <button
                className="btn-pill btn-primary"
                onClick={() => {
                  onRequestChanges(changeTarget, changeComment)
                  setShowChangesModal(false)
                }}
              >
                SUBMIT CHANGES
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ABORT CONFIRMATION MODAL */}
      {showAbortModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--accent-red)',
              padding: '24px',
              maxWidth: '440px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: 'var(--accent-red)' }}>
              ABORT MIGRATION RUN?
            </span>
            <p style={{ fontSize: '12px', color: 'var(--text-primary)' }}>
              Aborting drops the isolated staging table ({state.staging_entity}) and prevents any promotion to production silver tables.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <button className="btn-pill btn-secondary" onClick={() => setShowAbortModal(false)}>
                CANCEL
              </button>
              <button
                className="btn-pill btn-destructive"
                onClick={() => {
                  onAbort()
                  setShowAbortModal(false)
                }}
              >
                CONFIRM ABORT
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
