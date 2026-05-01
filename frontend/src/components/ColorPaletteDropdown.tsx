import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';

// ---------------------------------------------------------------------------
// Color Palette definitions
// ---------------------------------------------------------------------------

export interface ColorPalette {
  name: string;
  colors: string[];
}

export const COLOR_PALETTES: ColorPalette[] = [
  {
    name: 'FRBSF Default',
    colors: ['#2e5e8b', '#8baf3e', '#fcc62d', '#88cde5', '#b63b36', '#474747'],
  },
  {
    name: 'Vivid',
    colors: ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4'],
  },
  {
    name: 'Pastel',
    colors: ['#a1c9f4', '#ffb482', '#8de5a1', '#ff9f9b', '#d0bbff', '#fffea3'],
  },
  {
    name: 'Earth Tones',
    colors: ['#8c510a', '#d8b365', '#5ab4ac', '#01665e', '#c7eae5', '#7a5230'],
  },
  {
    name: 'Monochrome Blue',
    colors: ['#08306b', '#2171b5', '#4292c6', '#6baed6', '#9ecae1', '#c6dbef'],
  },
  {
    name: 'Tableau 10',
    colors: ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'],
  },
];

// ---------------------------------------------------------------------------
// Swatch row — renders a row of color circles
// ---------------------------------------------------------------------------

const SwatchRow: React.FC<{ colors: string[]; size?: number }> = ({ colors, size = 14 }) => (
  <div style={{ display: 'flex', gap: 3 }}>
    {colors.map((c, i) => (
      <span
        key={i}
        style={{
          display: 'inline-block',
          width: size,
          height: size,
          borderRadius: '50%',
          background: c,
          border: '1px solid rgba(0,0,0,0.15)',
        }}
      />
    ))}
  </div>
);

// ---------------------------------------------------------------------------
// Main dropdown component
// ---------------------------------------------------------------------------

const ColorPaletteDropdown: React.FC = () => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const chartState = useAppStore((s) => s.chartState);
  const setChartState = useAppStore((s) => s.setChartState);
  const activePaletteName = useAppStore((s) => s.activePaletteName);
  const setActivePaletteName = useAppStore((s) => s.setActivePaletteName);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open]);

  const applyPalette = useCallback(
    (palette: ColorPalette) => {
      setActivePaletteName(palette.name);
      setOpen(false);

      if (!chartState) return;

      // Update series colors (cycle through palette if more series than colors)
      const newSeries = chartState.series.map((s, i) => ({
        ...s,
        color: palette.colors[i % palette.colors.length],
      }));

      // Update legend entry colors to match
      const newLegend = {
        ...chartState.legend,
        entries: chartState.legend.entries.map((entry) => {
          const matchingSeries = newSeries.find((s) => s.name === entry.series_name);
          return matchingSeries ? { ...entry, color: matchingSeries.color } : entry;
        }),
      };

      setChartState({
        ...chartState,
        series: newSeries,
        legend: newLegend,
      });
    },
    [chartState, setChartState, setActivePaletteName],
  );

  const activePalette = COLOR_PALETTES.find((p) => p.name === activePaletteName) ?? COLOR_PALETTES[0];

  return (
    <div ref={menuRef} style={{ position: 'relative' }}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          fontSize: 12,
          border: '1px solid #ccc',
          borderRadius: 4,
          background: '#fff',
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}
        title="Color Palette"
      >
        <SwatchRow colors={activePalette.colors.slice(0, 4)} size={10} />
        <span style={{ fontSize: 11 }}>{activePalette.name}</span>
        <span style={{ fontSize: 9, marginLeft: 2 }}>{open ? '▲' : '▼'}</span>
      </button>

      {/* Dropdown menu */}
      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 4,
            background: '#fff',
            border: '1px solid #ccc',
            borderRadius: 6,
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            zIndex: 1200,
            minWidth: 240,
            padding: 6,
          }}
        >
          {COLOR_PALETTES.map((palette) => {
            const isActive = palette.name === activePaletteName;
            return (
              <button
                key={palette.name}
                onClick={() => applyPalette(palette)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: '100%',
                  padding: '8px 10px',
                  border: 'none',
                  borderRadius: 4,
                  background: isActive ? '#e8f0fe' : 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: 12,
                  fontWeight: isActive ? 600 : 400,
                  color: '#333',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = '#f5f5f5';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = isActive ? '#e8f0fe' : 'transparent';
                }}
              >
                <SwatchRow colors={palette.colors} size={14} />
                <span>{palette.name}</span>
                {isActive && <span style={{ marginLeft: 'auto', fontSize: 11, color: '#1a73e8' }}>✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ColorPaletteDropdown;
