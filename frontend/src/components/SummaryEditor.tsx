import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useAppStore } from '../store/appStore';
import { generateSummary } from '../api/client';
import type { ChartContext } from '../types';

const SummaryEditor: React.FC = () => {
  const summaryText = useAppStore((s) => s.summaryText);
  const setSummaryText = useAppStore((s) => s.setSummaryText);
  const chartState = useAppStore((s) => s.chartState);
  const [generating, setGenerating] = useState(false);
  const [isPreviewMode, setIsPreviewMode] = useState(true);

  const handleGenerate = async () => {
    if (!chartState) return;
    setGenerating(true);
    try {
      const context: ChartContext = {
        chart_state: chartState,
        dataset_summary: '',
        dataset_sample: [],
      };
      const text = await generateSummary(chartState.dataset_path, context);
      setSummaryText(text);
      setIsPreviewMode(true);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <h2 style={{ fontSize: 14, margin: 0 }}>Executive Summary</h2>
        <button
          onClick={handleGenerate}
          disabled={generating || !chartState}
          style={{
            fontSize: 12,
            padding: '2px 8px',
            cursor: generating || !chartState ? 'not-allowed' : 'pointer',
          }}
        >
          {generating ? 'Generating…' : 'Generate Summary'}
        </button>
        <button
          onClick={() => setIsPreviewMode(!isPreviewMode)}
          disabled={!summaryText}
          style={{
            fontSize: 12,
            padding: '2px 8px',
            cursor: !summaryText ? 'not-allowed' : 'pointer',
            marginLeft: 'auto',
          }}
        >
          {isPreviewMode ? 'Edit' : 'Preview'}
        </button>
      </div>
      {isPreviewMode ? (
        <div
          style={{
            width: '100%',
            flex: 1,
            minHeight: 80,
            overflowY: 'auto',
            padding: 12,
            border: '1px solid #ccc',
            borderRadius: 4,
            boxSizing: 'border-box',
            backgroundColor: '#fafafa',
          }}
        >
          <ReactMarkdown
            components={{
              h1: ({ node, ...props }) => <h1 style={{ fontSize: 20, marginTop: 16, marginBottom: 8 }} {...props} />,
              h2: ({ node, ...props }) => <h2 style={{ fontSize: 18, marginTop: 14, marginBottom: 6 }} {...props} />,
              h3: ({ node, ...props }) => <h3 style={{ fontSize: 16, marginTop: 12, marginBottom: 4 }} {...props} />,
              p: ({ node, ...props }) => <p style={{ marginBottom: 8, lineHeight: 1.6 }} {...props} />,
              ul: ({ node, ...props }) => <ul style={{ marginLeft: 20, marginBottom: 8 }} {...props} />,
              ol: ({ node, ...props }) => <ol style={{ marginLeft: 20, marginBottom: 8 }} {...props} />,
              li: ({ node, ...props }) => <li style={{ marginBottom: 4 }} {...props} />,
              strong: ({ node, ...props }) => <strong style={{ fontWeight: 600 }} {...props} />,
              code: ({ node, ...props }) => <code style={{ backgroundColor: '#e8e8e8', padding: '2px 4px', borderRadius: 3, fontSize: 12 }} {...props} />,
            }}
          >
            {summaryText || 'No summary available.'}
          </ReactMarkdown>
        </div>
      ) : (
        <textarea
          value={summaryText}
          onChange={(e) => setSummaryText(e.target.value)}
          placeholder="Summary will appear here after chart generation."
          style={{
            width: '100%',
            flex: 1,
            minHeight: 80,
            resize: 'none',
            overflowY: 'auto',
            fontFamily: 'inherit',
            fontSize: 13,
            padding: 8,
            border: '1px solid #ccc',
            borderRadius: 4,
            boxSizing: 'border-box',
          }}
        />
      )}
    </div>
  );
};

export default SummaryEditor;
