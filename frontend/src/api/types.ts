// Request Types

export interface ProcessRequest {
    Do_reset: number;
    file_id?: string;
}

export interface ScrapeRequest {
    base_url: string;
    library_name: string;
    Do_reset: number;
}

export interface Library {
    id: number;
    name: string;
}

export interface LibrariesResponse {
    signal: string;
    libraries: Library[];
}

export interface ScrapeResponse {
    signal: string;
    Inserted_chunks: number;
    processed_pages: number;
    total_pages_scraped: number;
}

export interface PushRequest {
    do_reset: number;
    project_name?: string;
}

export interface ChatMessageForRequest {
    role: "user" | "assistant";
    content: string;
}

export interface SearchRequest {
    text: string;
    limit: number;
    project_name?: string;
    chat_history?: ChatMessageForRequest[];
}

// Response Types

export interface HealthResponse {
    app_name: string;
    app_version: string;
}

export interface UploadResponse {
    signal: string;
    file_id: string;
}

export interface ProcessResponse {
    signal: string;
    Inserted_chunks: number;
    processed_files: number;
}

export interface PushResponse {
    Signal: string;
    InsertedItemsCount: number;
}

export interface CollectionInfo {
    vectors_count?: number;
    points_count?: number;
    indexed_vectors_count?: number;
    record_count?: number;
    table_info?: {
        schema_name?: string;
        table_name?: string;
        table_owner?: string;
        table_space?: string | null;
        has_indexes?: boolean;
    };
}

export interface IndexInfoResponse {
    Signal: string;
    CollectionInfo: CollectionInfo;
}

export interface SearchResult {
    text: string;
    score: number;
    metadata?: Record<string, unknown>;
}

export interface SearchResponse {
    Signal: string;
    Results: SearchResult[];
}

export interface AnswerResponse {
    Signal: string;
    Answer: string;
    FullPrompt: string;
    ChatHistory: unknown[];
}

export interface ErrorResponse {
    signal?: string;
    Signal?: string;
    error?: string;
}

// Chat Types

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
    metadata?: {
        fullPrompt?: string;
        chatHistory?: unknown[];
    };
}

// Upload Types

export interface UploadedFile {
    id: string;
    name: string;
    size: number;
    status: 'pending' | 'uploading' | 'uploaded' | 'error';
    error?: string;
}
