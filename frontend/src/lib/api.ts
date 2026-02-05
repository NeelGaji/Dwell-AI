/**
 * API Client for Pocket Planner Backend
 * 
 * Updated with longer timeouts for layout generation
 */

import axios, { AxiosError } from 'axios';
import type {
    AnalyzeRequest,
    AnalyzeResponse,
    OptimizeRequest,
    OptimizeResponse,
    RenderRequest,
    RenderResponse,
    PerspectiveRequest,
    PerspectiveResponse,
    ChatEditRequest,
    ChatEditResponse,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Standard API client
const api = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 60000, // 60 second default timeout
});

// Long-running operations client (for optimize and perspective)
const longApi = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 180000, // 3 minute timeout for layout generation
});

// Error handler
function handleApiError(error: unknown): never {
    if (error instanceof AxiosError) {
        if (error.code === 'ECONNABORTED') {
            throw new Error('Request timed out. The server is taking too long to respond.');
        }
        const message = error.response?.data?.detail || error.message;
        throw new Error(message);
    }
    throw error;
}

/**
 * Analyze a room image and extract furniture objects
 */
export async function analyzeRoom(imageBase64: string): Promise<AnalyzeResponse> {
    try {
        const response = await api.post<AnalyzeResponse>('/analyze', {
            image_base64: imageBase64,
        } satisfies AnalyzeRequest);
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}

/**
 * Optimize room layout while respecting locked objects
 * Uses longer timeout due to multiple AI operations
 */
export async function optimizeLayout(request: OptimizeRequest): Promise<OptimizeResponse> {
    try {
        const response = await longApi.post<OptimizeResponse>('/optimize', request);
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}

/**
 * Render the optimized layout as an edited image
 */
export async function renderLayout(request: RenderRequest): Promise<RenderResponse> {
    try {
        const response = await api.post<RenderResponse>('/render', request);
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}

/**
 * Generate a photorealistic perspective view of the layout
 * Uses longer timeout due to image generation
 */
export async function generatePerspective(request: PerspectiveRequest): Promise<PerspectiveResponse> {
    try {
        const response = await longApi.post<PerspectiveResponse>('/render/perspective', request);
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}

/**
 * Process a chat edit command
 */
export async function chatEdit(request: ChatEditRequest): Promise<ChatEditResponse> {
    try {
        const response = await longApi.post<ChatEditResponse>('/chat/edit', request);
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<{ status: string; version: string }> {
    try {
        const response = await axios.get(`${API_URL}/health`, { timeout: 5000 });
        return response.data;
    } catch (error) {
        handleApiError(error);
    }
}