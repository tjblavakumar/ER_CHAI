import axios, { AxiosError } from 'axios';
import { toast } from 'react-toastify';
import type {
  AIResponse,
  ChartContext,
  ChartState,
  ErrorResponse,
  IngestionResult,
  Project,
  ProjectCreate,
  ProjectSummary,
  ProjectUpdate,
} from '../types';

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: '/api',
});

// ---------------------------------------------------------------------------
// Centralized error interceptor — shows toast notifications
// ---------------------------------------------------------------------------

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response?.data?.message) {
      toast.error(error.response.data.message);
    } else if (error.request) {
      toast.error('Unable to reach the server. Please check your connection.');
    } else {
      toast.error('An unexpected error occurred.');
    }
    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

export async function ingestFromUrl(url: string): Promise<IngestionResult> {
  const { data } = await api.post<IngestionResult>('/ingest/url', { url });
  return data;
}

export async function ingestFromFile(
  file: File,
  referenceImage?: File,
): Promise<IngestionResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (referenceImage) {
    formData.append('reference_image', referenceImage);
  }
  const { data } = await api.post<IngestionResult>('/ingest/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ---------------------------------------------------------------------------
// AI Assistant
// ---------------------------------------------------------------------------

export async function aiChat(
  sessionId: string,
  message: string,
  chartContext: ChartContext,
): Promise<AIResponse> {
  const { data } = await api.post<AIResponse>('/ai/chat', {
    session_id: sessionId,
    message,
    chart_context: chartContext,
  });
  return data;
}

export async function aiReset(sessionId: string): Promise<void> {
  await api.post('/ai/reset', { session_id: sessionId });
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export async function generateSummary(
  datasetPath: string,
  chartContext: ChartContext,
): Promise<string> {
  const { data } = await api.post<{ summary: string }>('/summary/generate', {
    dataset_path: datasetPath,
    chart_context: chartContext,
  });
  return data.summary;
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export async function exportPython(projectId: string): Promise<Blob> {
  const { data } = await api.get(`/export/python/${projectId}`, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function exportR(projectId: string): Promise<Blob> {
  const { data } = await api.get(`/export/r/${projectId}`, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function exportPdf(projectId: string): Promise<Blob> {
  const { data } = await api.get(`/export/pdf/${projectId}`, {
    responseType: 'blob',
  });
  return data as Blob;
}

// ---------------------------------------------------------------------------
// Direct Export (no saved project required)
// ---------------------------------------------------------------------------

export async function exportPythonDirect(chartState: ChartState): Promise<Blob> {
  const { data } = await api.post('/export/python', { chart_state: chartState }, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function exportRDirect(chartState: ChartState): Promise<Blob> {
  const { data } = await api.post('/export/r', { chart_state: chartState }, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function exportPdfDirect(chartState: ChartState, summary: string): Promise<Blob> {
  const { data } = await api.post('/export/pdf', { chart_state: chartState, summary }, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function exportPdfWithImage(imageBlob: Blob, summary: string): Promise<Blob> {
  const formData = new FormData();
  formData.append('canvas_image', imageBlob, 'chart.png');
  formData.append('summary', summary);
  const { data } = await api.post('/export/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  });
  return data as Blob;
}

// ---------------------------------------------------------------------------
// Projects CRUD
// ---------------------------------------------------------------------------

export async function listProjects(): Promise<ProjectSummary[]> {
  const { data } = await api.get<ProjectSummary[]>('/projects');
  return data;
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  const { data } = await api.post<Project>('/projects', payload);
  return data;
}

export async function getProject(projectId: string): Promise<Project> {
  const { data } = await api.get<Project>(`/projects/${projectId}`);
  return data;
}

export async function updateProject(
  projectId: string,
  payload: ProjectUpdate,
): Promise<Project> {
  const { data } = await api.put<Project>(`/projects/${projectId}`, payload);
  return data;
}

export async function deleteProject(projectId: string): Promise<void> {
  await api.delete(`/projects/${projectId}`);
}

export async function loadDatasetRows(
  datasetPath: string,
): Promise<Record<string, unknown>[]> {
  const { data } = await api.post<{ rows: Record<string, unknown>[] }>(
    '/dataset/rows',
    { dataset_path: datasetPath },
  );
  return data.rows;
}
