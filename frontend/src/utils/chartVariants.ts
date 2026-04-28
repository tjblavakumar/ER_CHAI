import type { ChartState } from '../types';

export interface ChartVariant {
  label: string;
  description: string;
  chartState: ChartState;
}

/**
 * Deep clone a chart state to ensure no shared references.
 */
function deepClone(state: ChartState): ChartState {
  return JSON.parse(JSON.stringify(state));
}

/**
 * Generate chart style variants from a base chart state.
 * Creates line, area, bar, and optionally the reference-styled version.
 */
export function generateChartVariants(
  baseState: ChartState,
  referenceState?: ChartState | null,
): ChartVariant[] {
  const variants: ChartVariant[] = [];

  // If we have a reference-styled version, show it first
  if (referenceState) {
    variants.push({
      label: 'Reference Style',
      description: 'Matches the uploaded reference image styling',
      chartState: deepClone(referenceState),
    });
  }

  // Check if this is categorical data
  const isCategorical = !!(baseState.category_column && baseState.group_column);

  if (isCategorical) {
    // For categorical data, only bar chart variants make sense
    const barBySeries = deepClone(baseState);
    barBySeries.chart_type = 'bar';
    barBySeries.bar_grouping = 'by_series';
    barBySeries.series = barBySeries.series.map((s) => ({ ...s, chart_type: 'bar' }));
    variants.push({
      label: 'Grouped by Period',
      description: 'Bars grouped by time period, categories side by side',
      chartState: barBySeries,
    });

    const barByCategory = deepClone(baseState);
    barByCategory.chart_type = 'bar';
    barByCategory.bar_grouping = 'by_category';
    barByCategory.series = barByCategory.series.map((s) => ({ ...s, chart_type: 'bar' }));
    variants.push({
      label: 'Grouped by Category',
      description: 'Bars grouped by category with sub-bars per period',
      chartState: barByCategory,
    });

    return variants;
  }

  // Line chart variant
  const lineState = deepClone(baseState);
  lineState.chart_type = 'line';
  lineState.series = lineState.series.map((s) => ({ ...s, chart_type: 'line' }));
  variants.push({
    label: 'Line Chart',
    description: 'Clean line chart — good for trends over time',
    chartState: lineState,
  });

  // Area chart variant
  const areaState = deepClone(baseState);
  areaState.chart_type = 'area';
  areaState.series = areaState.series.map((s) => ({ ...s, chart_type: 'area' }));
  variants.push({
    label: 'Area Chart',
    description: 'Filled area chart — emphasizes volume and magnitude',
    chartState: areaState,
  });

  // Bar chart variant
  const barState = deepClone(baseState);
  barState.chart_type = 'bar';
  barState.series = barState.series.map((s) => ({ ...s, chart_type: 'bar' }));
  variants.push({
    label: 'Bar Chart',
    description: 'Bar chart — good for comparing discrete values',
    chartState: barState,
  });

  return variants;
}
