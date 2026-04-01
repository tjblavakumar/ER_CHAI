import React, { useState } from 'react';
import { useAppStore } from '../store/appStore';
import { generateSummary } from '../api/client';
import type { ChartContext } from '../types';

const SummaryEditor: React.FC = () => {
  const summaryText = useAppStore((s) => s.summaryText);
  const setSummaryText = useAppStore((s) => s.setSummaryText);
  const chartState = useAppStore((s) => s.chartState);
  const [generating, setGenerating] = useState(false);

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
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
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
      </div>
      <textarea
        value={summaryText}
        onChange={(e) => setSummaryText(e.target.value)}
        placeholder="Summary will appear here after chart generation."
        style={{
          width: '100%',
          minHeight: 200,
          maxHeight: 400,
          resize: 'vertical',
          overflowY: 'auto',
          fontFamily: 'inherit',
          fontSize: 13,
          padding: 8,
          border: '1px solid #ccc',
          borderRadius: 4,
          boxSizing: 'border-box',
        }}
      />
    </div>
  );
};

export default SummaryEditor;
