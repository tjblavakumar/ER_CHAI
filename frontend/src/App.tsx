import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAppStore } from './store/appStore';
import { ingestFromUrl, ingestFromFile, generateSummary, reanalyzeChart } from './api/client';
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
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const setIsLoading = useAppStore((s) => s.setIsLoading);
  const setLoadingMessage = useAppStore((s) => s.setLoadingMessage);
  const setReferenceImageFile = useAppStore((s) => s.setReferenceImageFile);
  const isLoading = useAppStore((s) => s.isLoading);

  const [fredUrl, setFredUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // FRED URL ingestion flow
  const handleFredIngest = useCallback(async () => {
    const url = fredUrl.trim();
    if (!url) return;
    setIsLoading(true);
    try {
      setLoadingMessage('Downloading data from FRED...');
      const result = await ingestFromUrl(url);
      setLoadingMessage('Rendering chart...');
      setChartState(result.chart_state);
      setDatasetInfo(result.dataset_info);
      setDatasetRows(result.dataset_rows ?? null);
      setFredUrl('');
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [fredUrl, setChartState, setDatasetInfo, setIsLoading, setLoadingMessage, setDatasetRows]);

  // File upload ingestion flow
  const handleFileUpload = useCallback(async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    const refImage = imageInputRef.current?.files?.[0];
    // Store reference image in app store before ingestion
    if (refImage) {
      setReferenceImageFile(refImage);
    } else {
      setReferenceImageFile(null);
    }
    setIsLoading(true);
    try {
      setLoadingMessage(refImage
        ? 'Parsing data and analyzing reference image (this may take a moment)...'
        : 'Parsing data and generating chart...');
      const result = await ingestFromFile(file, refImage);
      setLoadingMessage('Rendering chart...');
      setChartState(result.chart_state);
      setDatasetInfo(result.dataset_info);
      setDatasetRows(result.dataset_rows ?? null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (imageInputRef.current) imageInputRef.current.value = '';
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [setChartState, setDatasetInfo, setIsLoading, setLoadingMessage, setReferenceImageFile, setDatasetRows]);

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
// Bedrock Status Indicator
// ---------------------------------------------------------------------------

const BedrockStatus: React.FC = () => {
  const [status, setStatus] = useState<{ active: boolean; model: string; error: string } | null>(null);

  useEffect(() => {
    fetch('/api/bedrock/status')
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ active: false, model: '', error: 'Unable to check' }));
  }, []);

  if (!status) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        color: status.active ? '#2e7d32' : '#c62828',
        padding: '2px 8px',
        borderRadius: 4,
        background: status.active ? '#e8f5e9' : '#ffebee',
      }}
      title={status.active ? `Model: ${status.model}` : `Error: ${status.error}`}
    >
      <span style={{ fontSize: 8 }}>{status.active ? '●' : '●'}</span>
      {status.active ? 'Bedrock Active' : 'Bedrock Offline'}
    </div>
  );
};

// ---------------------------------------------------------------------------
// App Shell (Req 6.1, 9.1, 10.1, 12.4, 2.5)
// ---------------------------------------------------------------------------

const App: React.FC = () => {
  const isLoading = useAppStore((s) => s.isLoading);
  const loadingMessage = useAppStore((s) => s.loadingMessage);
  const chartState = useAppStore((s) => s.chartState);
  const referenceImageFile = useAppStore((s) => s.referenceImageFile);
  const setChartState = useAppStore((s) => s.setChartState);
  const setDatasetRows = useAppStore((s) => s.setDatasetRows);
  const setIsLoading = useAppStore((s) => s.setIsLoading);
  const setLoadingMessage = useAppStore((s) => s.setLoadingMessage);
  const setSummaryText = useAppStore((s) => s.setSummaryText);

  const handleReanalyze = useCallback(async () => {
    if (!chartState || !referenceImageFile) return;
    setIsLoading(true);
    try {
      setLoadingMessage('Re-analyzing reference image...');
      const result = await reanalyzeChart(referenceImageFile, chartState.dataset_path);
      setLoadingMessage('Rendering chart...');
      setChartState(result.chart_state);
      setDatasetRows(result.dataset_rows ?? null);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [chartState, referenceImageFile, setChartState, setDatasetRows, setIsLoading, setLoadingMessage]);

  const handleGenerateSummary = useCallback(async () => {
    if (!chartState) return;
    setIsLoading(true);
    try {
      setLoadingMessage('Generating executive summary...');
      const context: ChartContext = {
        chart_state: chartState,
        dataset_summary: '',
        dataset_sample: [],
      };
      const summary = await generateSummary(chartState.dataset_path, context);
      setSummaryText(summary);
    } catch {
      // Error toast handled by API interceptor
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [chartState, setIsLoading, setLoadingMessage, setSummaryText]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Arial, sans-serif', position: 'relative' }}>
      {/* Persistent network error banner */}
      <NetworkBanner />

      {/* Full-screen loading overlay */}
      {isLoading && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: '32px 48px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
              textAlign: 'center',
              maxWidth: 400,
            }}
          >
            {/* Spinner */}
            <div
              style={{
                width: 40,
                height: 40,
                border: '4px solid #e0e0e0',
                borderTopColor: '#1a73e8',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                margin: '0 auto 16px',
              }}
            />
            <div style={{ fontSize: 15, fontWeight: 600, color: '#333', marginBottom: 6 }}>
              {loadingMessage || 'Processing...'}
            </div>
            <div style={{ fontSize: 12, color: '#888' }}>Please wait</div>
          </div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  onClick={handleReanalyze}
                  disabled={!chartState || !referenceImageFile || isLoading}
                  style={{
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: !chartState || !referenceImageFile || isLoading ? 'not-allowed' : 'pointer',
                    opacity: !chartState || !referenceImageFile || isLoading ? 0.6 : 1,
                  }}
                >
                  Reanalyze &amp; Regenerate
                </button>
                <button
                  onClick={handleGenerateSummary}
                  disabled={!chartState || isLoading}
                  style={{
                    padding: '4px 12px',
                    fontSize: 12,
                    cursor: !chartState || isLoading ? 'not-allowed' : 'pointer',
                    opacity: !chartState || isLoading ? 0.6 : 1,
                  }}
                >
                  Exe Summary
                </button>
              </div>
              <BedrockStatus />
              <ExportToolbar />
            </div>
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
