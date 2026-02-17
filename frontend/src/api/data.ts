import { apiClient, uploadFileWithProgress } from './client';
import type { UploadResponse, ProcessRequest, ProcessResponse, ScrapeRequest, ScrapeResponse, LibrariesResponse } from './types';

export const uploadFile = async (
    file: File,
    onProgress?: (progress: number) => void
): Promise<UploadResponse> => {
    const response = await uploadFileWithProgress(
        `/data/upload`,
        file,
        onProgress
    );
    return response.data;
};

export const processFiles = async (
    request: ProcessRequest
): Promise<ProcessResponse> => {
    const response = await apiClient.post<ProcessResponse>(
        `/data/process`,
        request
    );
    return response.data;
};

/** Scrape can take many minutes on slow connections; allow up to 15 minutes. */
const SCRAPE_REQUEST_TIMEOUT_MS = 15 * 60 * 1000;

export const scrapeDocumentation = async (
    request: ScrapeRequest
): Promise<ScrapeResponse> => {
    const response = await apiClient.post<ScrapeResponse>(
        `/data/scrape`,
        request,
        { timeout: SCRAPE_REQUEST_TIMEOUT_MS }
    );
    return response.data;
};

/** Request backend to stop the currently running scrape. Safe to call if no scrape is running. */
export const cancelScrapeDocumentation = async (): Promise<{ signal: string; message: string }> => {
    const response = await apiClient.post<{ signal: string; message: string }>(
        `/data/scrape-cancel`
    );
    return response.data;
};

/** Run chunking from a saved scrape cache (e.g. after frontend timed out). No refetch. */
export const processScrapeCache = async (base_url: string): Promise<ScrapeResponse> => {
    const response = await apiClient.post<ScrapeResponse>(
        `/data/process-scrape-cache`,
        { base_url },
        { timeout: 15 * 60 * 1000 }
    );
    return response.data;
};

export const resetProject = async (): Promise<void> => {
    await apiClient.delete(`/data/assets`);
};

export const getLibraries = async (): Promise<LibrariesResponse> => {
    const response = await apiClient.get<LibrariesResponse>(`/data/libraries`);
    return response.data;
};
