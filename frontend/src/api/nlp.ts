import { apiClient } from './client';
import type {
    PushRequest,
    PushResponse,
    IndexInfoResponse,
    SearchRequest,
    SearchResponse,
    AnswerResponse,
} from './types';

export const pushToIndex = async (
    request: PushRequest
): Promise<PushResponse> => {
    const response = await apiClient.post<PushResponse>(
        `/nlp/index/push`,
        request
    );
    return response.data;
};

export const getIndexInfo = async (): Promise<IndexInfoResponse> => {
    const response = await apiClient.get<IndexInfoResponse>(
        `/nlp/index/info`
    );
    return response.data;
};

export const searchIndex = async (
    request: SearchRequest
): Promise<SearchResponse> => {
    const response = await apiClient.post<SearchResponse>(
        `/nlp/index/search`,
        request
    );
    return response.data;
};

export const getAnswer = async (
    request: SearchRequest
): Promise<AnswerResponse> => {
    const response = await apiClient.post<AnswerResponse>(
        `/nlp/index/answer`,
        request
    );
    return response.data;
};
