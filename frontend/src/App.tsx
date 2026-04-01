import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAppStore } from './store/appStore';
import { ingestFromUrl, ingestFromFile, generateSummary } from './api/client';
import type { ChartContext } from './types';

import ProjectList from './components/ProjectList';
import CanvasEditor from './components/CanvasEditor';
import ControlsPanel from './components/ControlsPanel';
import SummaryEditor from './components/SummaryEditor';
import ExportToolbar from './components/ExportToolbar';
import AIChatWindow from './components/AIChatWindow';

// ---------------------------------------------------------------------------
// Network error banner — polls /api/health to detect connectivity (Req 2.5)
// ---------------------------------------------------------------------------

const NetworkBanner: React.FC = () => {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        await fetch('/api/health', { method: 'GET', cache: 'no-store' });
        if (mounted) setOffline(false);
      } catch {
        if (mounted) setOffline(true);
      }
    };

    check();
    const id = setInterval(check, 10_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="alert"
      style={{
        background: '#d32f2f',
        color: '#fff',
        textAlign: 'center',
        padding: '6px 12px',
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      Unable to reach the server. Please check your connection.
    </div>
  );
};

// ---------------------------------------------------------------------------
// Data Ingestion Bar (Req 3.1, 3.2, 3.3, 4.1, 4.2, 4.5, 5.5, 12.1)
// ---------------------------------------------------------------------------

const DataIngestionBar: React.FC = () => {
  const setChartState = useAppStore((s) => s.setChartState);
  const setDatasetInfo = useAppStore((s) => s.setDatasetInfo);
  const setSummaryText = useAppStore((s) => s.setSummaryText);
  const setIsLoading = useAppStore((s) => s.setIsLoading);
  const isLoading = useAppStore((s) => s.isLoading);

  const [fredUrl, setFredUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Auto-generate summary after ingestion
  const autoGenerateSummary = useCallback(
    async (datasetPath: string, chartState: Parameters<typeof setChartState>[0]) => {
      try {
        const context: ChartContext = {
          chart_state: chartState,
          dataset_summary: '',
          dataset_sample: [],
        };
        const summary = await generateSummary(datasetPath, context);
        setSummaryText(summary);
      } catch {
        // Summary generation failure is non-blocking
      }
    },
    [setSummaryText],
  );

  // FRED URL ingestion flow
  const handleFredIngest = useCallback(async () => {
    const url = fredUrl.trim();
    if (!url) return;
    setIsLoading(true);
    try {
      const result = await ingestFromUrl(url);
      setChartState(result.chart_state);
      setDatasetInfo(result.dataset_info);
      setFredUrl('');
      // Auto-generate summary (Req 12.1)
      await autoGenerateSummary(result.dataset_path, result.chart_state);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
    }
  }, [fredUrl, setChartState, setDatasetInfo, setIsLoading, autoGenerateSummary]);

  // File upload ingestion flow
  const handleFileUpload = useCallback(async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    const refImage = imageInputRef.current?.files?.[0];
    setIsLoading(true);
    try {
      const result = await ingestFromFile(file, refImage);
      setChartState(result.chart_state);
      setDatasetInfo(result.dataset_info);
      // Clear file inputs
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (imageInputRef.current) imageInputRef.current.value = '';
      // Auto-generate summary (Req 12.1)
      await autoGenerateSummary(result.dataset_path, result.chart_state);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
    }
  }, [setChartState, setDatasetInfo, setIsLoading, autoGenerateSummary]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleFredIngest();
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 16px',
        borderBottom: '1px solid #e0e0e0',
        background: '#f5f7fa',
        flexWrap: 'wrap',
        fontSize: 13,
      }}
    >
      {/* FRED URL input */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label htmlFor="fred-url" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
          FRED URL:
        </label>
        <input
          id="fred-url"
          type="text"
          value={fredUrl}
          onChange={(e) => setFredUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://fred.stlouisfed.org/series/..."
          disabled={isLoading}
          style={{
            width: 280,
            padding: '4px 8px',
            border: '1px solid #ccc',
            borderRadius: 4,
            fontSize: 12,
          }}
        />
        <button
          onClick={handleFredIngest}
          disabled={isLoading || !fredUrl.trim()}
          style={{
            padding: '4px 12px',
            fontSize: 12,
            cursor: isLoading || !fredUrl.trim() ? 'not-allowed' : 'pointer',
            opacity: isLoading || !fredUrl.trim() ? 0.6 : 1,
          }}
        >
          {isLoading ? 'Loading…' : 'Ingest'}
        </button>
      </div>

      <span style={{ color: '#aaa' }}>|</span>

      {/* File upload */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label htmlFor="data-file" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
          Upload CSV/Excel:
        </label>
        <input
          id="data-file"
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          disabled={isLoading}
          style={{ fontSize: 12 }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label htmlFor="ref-image" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
          Reference image:
        </label>
        <input
          id="ref-image"
          ref={imageInputRef}
          type="file"
          accept="image/*"
          disabled={isLoading}
          style={{ fontSize: 12 }}
        />
      </div>

      <button
        onClick={handleFileUpload}
        disabled={isLoading}
        style={{
          padding: '4px 12px',
          fontSize: 12,
          cursor: isLoading ? 'not-allowed' : 'pointer',
          opacity: isLoading ? 0.6 : 1,
        }}
      >
        {isLoading ? 'Uploading…' : 'Upload & Ingest'}
      </button>
    </div>
  );
};

// ---------------------------------------------------------------------------
// App Shell (Req 6.1, 9.1, 10.1, 12.4, 2.5)
// ---------------------------------------------------------------------------

const App: React.FC = () => {
  const isLoading = useAppStore((s) => s.isLoading);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Arial, sans-serif' }}>
      {/* Persistent network error banner */}
      <NetworkBanner />

      {/* Loading indicator */}
      {isLoading && (
        <div
          style={{
            background: '#1a73e8',
            color: '#fff',
            textAlign: 'center',
            padding: '4px 0',
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Processing…
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left sidebar — Project List */}
        <aside
          style={{
            width: 220,
            borderRight: '1px solid #ddd',
            padding: 12,
            overflowY: 'auto',
            background: '#f9f9f9',
            flexShrink: 0,
          }}
        >
          <h2 style={{ fontSize: 15, margin: '0 0 10px' }}>Projects</h2>
          <ProjectList />
        </aside>

        {/* Main content area */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Header: title + export toolbar */}
          <header
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 16px',
              borderBottom: '1px solid #ddd',
              background: '#fff',
              flexShrink: 0,
            }}
          >
            <h1 style={{ fontSize: 18, margin: 0 }}>FRBSF Chart Builder</h1>
            <ExportToolbar />
          </header>

          {/* Data ingestion bar */}
          <DataIngestionBar />

          {/* Canvas + Controls */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* Center: Canvas Editor */}
            <section
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#f0f0f0',
                overflow: 'auto',
              }}
            >
              <CanvasEditor />
            </section>

            {/* Right sidebar: Controls Panel */}
            <aside
              style={{
                width: 270,
                borderLeft: '1px solid #ddd',
                padding: 12,
                overflowY: 'auto',
                background: '#fafafa',
                flexShrink: 0,
              }}
            >
              <h2 style={{ fontSize: 15, margin: '0 0 10px' }}>Controls</h2>
              <ControlsPanel />
            </aside>
          </div>

          {/* Bottom: Summary Editor */}
          <section
            style={{
              borderTop: '1px solid #ddd',
              padding: 12,
              background: '#fff',
              flexShrink: 0,
            }}
          >
            <SummaryEditor />
          </section>
        </main>
      </div>

      {/* Floating overlay: AI Chat Window */}
      <AIChatWindow />
    </div>
  );
};

export default App;
