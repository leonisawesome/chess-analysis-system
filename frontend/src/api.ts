const API_URL = 'http://localhost:8000';

export interface Chunk {
    chunk_id: number;
    book_title: string;
    text: string;
    fen: string;
    quality_score: number;
    is_instructional: boolean;
}

export interface SearchResult {
    results: Chunk[];
    total: number;
}

export const searchConcepts = async (query: string): Promise<SearchResult> => {
    const response = await fetch(`${API_URL}/search/concept?query=${encodeURIComponent(query)}&limit=5`);
    if (!response.ok) {
        throw new Error('Failed to fetch concepts');
    }
    return response.json();
};

export const searchByFen = async (fen: string): Promise<SearchResult> => {
    const response = await fetch(`${API_URL}/search/fen?fen=${encodeURIComponent(fen)}&limit=5`);
    if (!response.ok) {
        throw new Error('Failed to fetch similar positions');
    }
    return response.json();
};
