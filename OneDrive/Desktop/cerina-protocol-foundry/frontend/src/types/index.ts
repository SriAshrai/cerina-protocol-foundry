// frontend/src/types/index.ts
export interface Review {
    agent: string;
    notes: string;
    score: number;
    reasoning: string;
}

export interface GraphState {
    draft: string;
    draft_history: string[];
    reviews: Review[];
    scores: {
        safety: number;
        clinical: number;
    };
    iteration_count: number;
    supervisor_feedback: string;
    user_intent: string;
    error?: string;
    metadata?: {
        [key: string]: any;
    };
}

export interface TaskMetadata {
    intent: string;
    created_at: string;
    last_update: string;
    iterations: number;
    duration_seconds?: number;
}

export interface APIResponse {
    success: boolean;
    message: string;
    data?: {
        thread_id: string;
        status: string;
        state: GraphState;
        metadata: TaskMetadata;
    };
    timestamp: string;
}

export interface Task {
    thread_id: string;
    status: string;
    intent: string;
    created_at: string;
    iterations: number;
}