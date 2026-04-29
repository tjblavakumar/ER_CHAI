import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import { aiChat } from '../api/client';
import type { ChartContext, ChartState, ChartConfigDelta } from '../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildChartContext(
  chartState: ChartState,
  datasetRows: Record<string, unknown>[] | null,
): ChartContext {
  // Send all rows so the AI has full data access for analysis, anomaly detection, etc.
  // Typical economic datasets are small (< 1000 rows), well within model context limits.
  const allRows = datasetRows ?? [];
  return {
    chart_state: chartState,
    dataset_summary: `Columns: ${chartState.dataset_columns.join(', ')}; Rows: ${allRows.length}; Path: ${chartState.dataset_path}`,
    dataset_sample: allRows,
  };
}

function applyDelta(state: ChartState, delta: ChartConfigDelta): ChartState {
  // Merge annotations: append new ones, update existing by id
  // If _replace_annotations flag is set, do full replacement (for removals)
  let mergedAnnotations = state.annotations;
  if (delta.annotations != null) {
    // Check for delete markers — any annotation with _delete flag
    const deleteIds = new Set(
      (delta.annotations as unknown as Array<Record<string, unknown>>)
        .filter((a) => a._delete === true)
        .map((a) => a.id as string),
    );

    if (deleteIds.size > 0) {
      // Remove annotations with matching IDs
      mergedAnnotations = state.annotations.filter((a) => !deleteIds.has(a.id));
    } else {
      // Normal merge: append new, update existing
      const existingIds = new Set(state.annotations.map((a) => a.id));
      const updated = state.annotations.map((existing) => {
        const replacement = delta.annotations!.find((d) => d.id === existing.id);
        return replacement ?? existing;
      });
      const newOnes = delta.annotations.filter((d) => !existingIds.has(d.id));
      mergedAnnotations = [...updated, ...newOnes];
    }
  }

  // When global chart_type changes, propagate to all series
  const newChartType = delta.chart_type ?? state.chart_type;
  let mergedSeries = delta.series ?? state.series;
  if (delta.chart_type != null && delta.chart_type !== state.chart_type && !delta.series) {
    mergedSeries = state.series.map((s) => ({
      ...s,
      chart_type: delta.chart_type!,
    }));
  }

  return {
    ...state,
    chart_type: newChartType,
    ...(delta.title != null && { title: delta.title }),
    ...(delta.axes != null && { axes: delta.axes }),
    series: mergedSeries,
    ...(delta.legend != null && { legend: delta.legend }),
    ...(delta.gridlines != null && { gridlines: delta.gridlines }),
    annotations: mergedAnnotations,
    ...(delta.data_table != null && { data_table: delta.data_table }),
    ...(delta.bar_grouping != null && { bar_grouping: delta.bar_grouping }),
    ...(delta.bar_stacking != null && { bar_stacking: delta.bar_stacking }),
    ...(delta.display_transforms != null && { display_transforms: delta.display_transforms }),
  };
}

// ---------------------------------------------------------------------------
// Resize constants
// ---------------------------------------------------------------------------

const MIN_WIDTH = 300;
const MIN_HEIGHT = 350;
const MAX_WIDTH = 900;
const MAX_HEIGHT = 900;
const DEFAULT_WIDTH = 420;
const DEFAULT_HEIGHT = 520;
const DEFAULT_FONT_SIZE = 14;
const FONT_SIZE_OPTIONS = [12, 13, 14, 16, 18];
const EDGE_HANDLE = 6; // px from edge that triggers resize

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const fabStyle: React.CSSProperties = {
  position: 'fixed',
  bottom: 24,
  right: 24,
  width: 52,
  height: 52,
  borderRadius: '50%',
  background: '#1a73e8',
  color: '#fff',
  border: 'none',
  fontSize: 24,
  cursor: 'pointer',
  boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '10px 14px',
  background: '#1a73e8',
  color: '#fff',
  fontSize: 14,
  fontWeight: 600,
};

const messagesStyle: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
};

const inputBarStyle: React.CSSProperties = {
  display: 'flex',
  borderTop: '1px solid #e0e0e0',
  padding: 8,
  gap: 6,
};

const sendBtnStyle: React.CSSProperties = {
  background: '#1a73e8',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '6px 14px',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 600,
};

const closeBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#fff',
  fontSize: 18,
  cursor: 'pointer',
  lineHeight: 1,
};

const undoBtnStyle: React.CSSProperties = {
  background: '#f5f5f5',
  border: '1px solid #ddd',
  borderRadius: 6,
  padding: '4px 10px',
  cursor: 'pointer',
  fontSize: 12,
  color: '#333',
  alignSelf: 'flex-start',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AIChatWindow: React.FC = () => {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [lastModifyIndex, setLastModifyIndex] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Resizable window state
  const [winWidth, setWinWidth] = useState(DEFAULT_WIDTH);
  const [winHeight, setWinHeight] = useState(DEFAULT_HEIGHT);
  const [fontSize, setFontSize] = useState(DEFAULT_FONT_SIZE);
  const resizingRef = useRef<{ edge: string; startX: number; startY: number; startW: number; startH: number } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);

  const aiChatOpen = useAppStore((s) => s.aiChatOpen);
  const setAiChatOpen = useAppStore((s) => s.setAiChatOpen);
  const chatMessages = useAppStore((s) => s.chatMessages);
  const addChatMessage = useAppStore((s) => s.addChatMessage);
  const chatSessionId = useAppStore((s) => s.chatSessionId);
  const chartState = useAppStore((s) => s.chartState);
  const datasetRows = useAppStore((s) => s.datasetRows);
  const setChartState = useAppStore((s) => s.setChartState);
  const undo = useAppStore((s) => s.undo);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // --- Resize logic ---
  const handleResizeMouseDown = useCallback((edge: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    resizingRef.current = {
      edge,
      startX: e.clientX,
      startY: e.clientY,
      startW: winWidth,
      startH: winHeight,
    };

    const handleMouseMove = (ev: MouseEvent) => {
      if (!resizingRef.current) return;
      const { edge: ed, startX, startY, startW, startH } = resizingRef.current;
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;

      let newW = startW;
      let newH = startH;

      // Left edge or top-left corner: dragging left increases width
      if (ed.includes('left')) newW = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startW - dx));
      // Top edge or top-left corner: dragging up increases height
      if (ed.includes('top')) newH = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, startH - dy));

      setWinWidth(newW);
      setWinHeight(newH);
    };

    const handleMouseUp = () => {
      resizingRef.current = null;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = edge === 'top-left' ? 'nwse-resize' : edge === 'left' ? 'ew-resize' : 'ns-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [winWidth, winHeight]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || !chartState || sending) return;

    setInput('');
    setSending(true);

    // Add user message
    addChatMessage({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    });

    try {
      const context = buildChartContext(chartState, datasetRows);
      const response = await aiChat(chatSessionId, text, context);

      if (response.type === 'chart_modify' && response.chart_delta) {
        // Direct apply (single option from AI)
        const latestChartState = useAppStore.getState().chartState;
        if (latestChartState) {
          const newState = applyDelta(latestChartState, response.chart_delta);
          useAppStore.getState().setChartState({ ...newState });
        }
        setLastModifyIndex(chatMessages.length + 1);

        addChatMessage({
          role: 'assistant',
          content: response.message,
          chartDelta: response.chart_delta,
          timestamp: new Date().toISOString(),
        });
      } else if (response.type === 'suggestion' && response.suggestions && response.suggestions.length > 0) {
        // Multiple suggestions — show as clickable options
        addChatMessage({
          role: 'assistant',
          content: response.message,
          suggestions: response.suggestions as { label: string; delta: ChartConfigDelta }[],
          timestamp: new Date().toISOString(),
        });
      } else if (response.type === 'summary_update') {
        // Replace or append based on AI's intent detection
        const currentSummary = useAppStore.getState().summaryText;
        const shouldReplace = response.replace_summary ?? false;
        
        const newSummary = shouldReplace || !currentSummary
          ? response.message
          : `${currentSummary}\n\n${response.message}`;
        
        useAppStore.getState().setSummaryText(newSummary);

        addChatMessage({
          role: 'assistant',
          content: shouldReplace ? 'Replaced the executive summary.' : 'Updated the executive summary.',
          timestamp: new Date().toISOString(),
        });
      } else {
        // data_qa — just display the text answer
        addChatMessage({
          role: 'assistant',
          content: response.message,
          timestamp: new Date().toISOString(),
        });
      }
    } catch {
      addChatMessage({
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      });
    } finally {
      setSending(false);
    }
  }, [input, chartState, sending, chatSessionId, addChatMessage, setChartState, chatMessages.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleUndo = () => {
    undo();
    setLastModifyIndex(null);
  };

  // Floating action button (always visible)
  const fab = (
    <button
      style={fabStyle}
      onClick={() => setAiChatOpen(!aiChatOpen)}
      aria-label={aiChatOpen ? 'Close AI Assistant' : 'Open AI Assistant'}
      title="AI Assistant"
    >
      💬
    </button>
  );

  if (!aiChatOpen) return fab;

  return (
    <>
      {fab}
      <div
        ref={windowRef}
        style={{
          position: 'fixed',
          bottom: 88,
          right: 24,
          width: winWidth,
          height: winHeight,
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1001,
          overflow: 'hidden',
        }}
        role="dialog"
        aria-label="AI Assistant Chat"
      >
        {/* Resize handle: top-left corner */}
        <div
          onMouseDown={(e) => handleResizeMouseDown('top-left', e)}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: 14,
            height: 14,
            cursor: 'nwse-resize',
            zIndex: 10,
          }}
        />
        {/* Resize handle: left edge */}
        <div
          onMouseDown={(e) => handleResizeMouseDown('left', e)}
          style={{
            position: 'absolute',
            top: 14,
            left: 0,
            width: EDGE_HANDLE,
            height: 'calc(100% - 14px)',
            cursor: 'ew-resize',
            zIndex: 10,
          }}
        />
        {/* Resize handle: top edge */}
        <div
          onMouseDown={(e) => handleResizeMouseDown('top', e)}
          style={{
            position: 'absolute',
            top: 0,
            left: 14,
            width: 'calc(100% - 14px)',
            height: EDGE_HANDLE,
            cursor: 'ns-resize',
            zIndex: 10,
          }}
        />

        {/* Header */}
        <div style={headerStyle}>
          <span>AI Assistant</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Font size selector */}
            <select
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              title="Chat font size"
              aria-label="Chat font size"
              style={{
                background: 'rgba(255,255,255,0.2)',
                color: '#fff',
                border: '1px solid rgba(255,255,255,0.4)',
                borderRadius: 4,
                padding: '2px 4px',
                fontSize: 11,
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              {FONT_SIZE_OPTIONS.map((s) => (
                <option key={s} value={s} style={{ color: '#333', background: '#fff' }}>
                  {s}px
                </option>
              ))}
            </select>
            <button style={closeBtnStyle} onClick={() => setAiChatOpen(false)} aria-label="Close">
              ✕
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={messagesStyle}>
          {chatMessages.length === 0 && (
            <p style={{ color: '#999', fontSize, textAlign: 'center', marginTop: 40 }}>
              Ask me to modify your chart or answer data questions.
            </p>
          )}
          {chatMessages.map((msg, i) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={i}
                style={{
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  background: isUser ? '#e3f2fd' : '#f5f5f5',
                  color: '#222',
                  borderRadius: 10,
                  padding: '8px 12px',
                  maxWidth: '85%',
                  fontSize,
                  lineHeight: 1.45,
                  wordBreak: 'break-word',
                }}
              >
                {msg.content}
                {/* Suggestion buttons */}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                    {msg.suggestions.map((s, si) => (
                      <button
                        key={si}
                        onClick={() => {
                          const latestState = useAppStore.getState().chartState;
                          if (latestState) {
                            const newState = applyDelta(latestState, s.delta);
                            useAppStore.getState().setChartState({ ...newState });
                            addChatMessage({
                              role: 'assistant',
                              content: `Applied: ${s.label}`,
                              timestamp: new Date().toISOString(),
                            });
                          }
                        }}
                        style={{
                          padding: '6px 12px',
                          fontSize: fontSize - 1,
                          border: '1px solid #1a73e8',
                          borderRadius: 6,
                          background: '#e8f0fe',
                          color: '#1a73e8',
                          cursor: 'pointer',
                          textAlign: 'left',
                          fontWeight: 500,
                        }}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* Undo button after last AI chart modification */}
          {lastModifyIndex !== null && lastModifyIndex === chatMessages.length - 1 && (
            <button style={undoBtnStyle} onClick={handleUndo}>
              ↩ Undo last change
            </button>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div style={inputBarStyle}>
          <input
            style={{
              flex: 1,
              border: '1px solid #ccc',
              borderRadius: 6,
              padding: '6px 10px',
              fontSize,
              outline: 'none',
            }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={chartState ? 'Type a message…' : 'Load a chart first'}
            disabled={!chartState || sending}
            aria-label="Chat message input"
          />
          <button
            style={{
              ...sendBtnStyle,
              fontSize: fontSize - 1,
              opacity: !chartState || sending || !input.trim() ? 0.5 : 1,
            }}
            onClick={handleSend}
            disabled={!chartState || sending || !input.trim()}
          >
            {sending ? '…' : 'Send'}
          </button>
        </div>
      </div>
    </>
  );
};

export default AIChatWindow;
