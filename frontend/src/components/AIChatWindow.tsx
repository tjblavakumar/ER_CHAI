import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import { aiChat } from '../api/client';
import type { ChartContext, ChartState, ChartConfigDelta } from '../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildChartContext(chartState: ChartState): ChartContext {
  return {
    chart_state: chartState,
    dataset_summary: `Columns: ${chartState.dataset_columns.join(', ')}; Path: ${chartState.dataset_path}`,
    dataset_sample: [],
  };
}

function applyDelta(state: ChartState, delta: ChartConfigDelta): ChartState {
  return {
    ...state,
    ...(delta.chart_type != null && { chart_type: delta.chart_type }),
    ...(delta.title != null && { title: delta.title }),
    ...(delta.axes != null && { axes: delta.axes }),
    ...(delta.series != null && { series: delta.series }),
    ...(delta.legend != null && { legend: delta.legend }),
    ...(delta.gridlines != null && { gridlines: delta.gridlines }),
    ...(delta.annotations != null && { annotations: delta.annotations }),
    ...(delta.data_table !== undefined && { data_table: delta.data_table }),
  };
}

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

const windowStyle: React.CSSProperties = {
  position: 'fixed',
  bottom: 88,
  right: 24,
  width: 350,
  height: 450,
  background: '#fff',
  borderRadius: 12,
  boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
  display: 'flex',
  flexDirection: 'column',
  zIndex: 1001,
  overflow: 'hidden',
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

const inputStyle: React.CSSProperties = {
  flex: 1,
  border: '1px solid #ccc',
  borderRadius: 6,
  padding: '6px 10px',
  fontSize: 13,
  outline: 'none',
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

  const aiChatOpen = useAppStore((s) => s.aiChatOpen);
  const setAiChatOpen = useAppStore((s) => s.setAiChatOpen);
  const chatMessages = useAppStore((s) => s.chatMessages);
  const addChatMessage = useAppStore((s) => s.addChatMessage);
  const chatSessionId = useAppStore((s) => s.chatSessionId);
  const chartState = useAppStore((s) => s.chartState);
  const setChartState = useAppStore((s) => s.setChartState);
  const undo = useAppStore((s) => s.undo);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

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
      const context = buildChartContext(chartState);
      const response = await aiChat(chatSessionId, text, context);

      if (response.type === 'chart_modify' && response.chart_delta) {
        // Apply delta — setChartState auto-pushes to undo history
        const newState = applyDelta(chartState, response.chart_delta);
        setChartState(newState);
        setLastModifyIndex(chatMessages.length + 1); // index of the assistant msg about to be added

        addChatMessage({
          role: 'assistant',
          content: response.message,
          chartDelta: response.chart_delta,
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
      <div style={windowStyle} role="dialog" aria-label="AI Assistant Chat">
        {/* Header */}
        <div style={headerStyle}>
          <span>AI Assistant</span>
          <button style={closeBtnStyle} onClick={() => setAiChatOpen(false)} aria-label="Close">
            ✕
          </button>
        </div>

        {/* Messages */}
        <div style={messagesStyle}>
          {chatMessages.length === 0 && (
            <p style={{ color: '#999', fontSize: 13, textAlign: 'center', marginTop: 40 }}>
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
                  maxWidth: '80%',
                  fontSize: 13,
                  lineHeight: 1.45,
                  wordBreak: 'break-word',
                }}
              >
                {msg.content}
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
            style={inputStyle}
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
