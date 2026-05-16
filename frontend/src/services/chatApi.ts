
export interface SourceNode {
  node_id: string;
  text: string;     // Content of the retrieval chunk
  score: number;    // Similarity score
  metadata: {
    course_id?: string;
    type?: string;  // e.g. 'desc' or 'review'
    [key: string]: any;
  };
}

export interface ChatResponse {
  response: string;           // The main answer from the chatbot
  sources: SourceNode[];      // List of reference citations
  intent?: {                  // Detected intent (optional)
    category: string;
    course_codes: string[];
    course_names: string[];
  };
  suggested_queries?: string[]; // Simplified access for UI
  latency_ms?: number;        // Total processing time
  latency_breakdown?: Record<string, number>; // Detailed timing info
}

export interface CourseName {
  course_id: string;
  course_name_th: string;
  category_64: string;
  competency_67: string;
  credits: number;
  faculty: string;
  doc_type: string;
  description: string;
  clos: string;
}

export interface ReviewSubmission {
  course_id: string;
  review_content: string;
  course_name: string;
  credits: string;
  faculty: string;
  category_64: string;
  competency_67: string;
}

export interface Review extends ReviewSubmission {
  id: number;
}

/**
 * Sends a chat query to the RAG API.
 * @param query The user's question or message.
 * @returns A Promise resolving to the structured ChatResponse.
 * @throws Error if the API call fails.
 */
export const fetchChatResponse = async (
  query: string, 
  signal?: AbortSignal,
  onStatus?: (status: string) => void,
  onToken?: (token: string) => void
): Promise<ChatResponse> => {
  const controller = new AbortController();
  // Extended timeout for streaming (streams can take longer overall, but first byte is fast)
  const timeoutId = setTimeout(() => controller.abort(), 120000); 

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    const response = await fetch(`${baseUrl}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let finalResult: ChatResponse | null = null;
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Holding the last potentially incomplete line in the buffer
      buffer = lines.pop() || ''; 

      for (const line of lines) {
        if (!line.trim()) continue;
        
        try {
          const event = JSON.parse(line);
          
          if (event.type === 'status' && onStatus) {
            onStatus(event.message);
          } else if (event.type === 'token' && onToken) {
            onToken(event.content);
          } else if (event.type === 'result') {
            // Backend sends flat JSON (e.g. { type: 'result', response: '...', sources: ... })
            // We assign the whole event object (casted) or specific fields
            finalResult = event as ChatResponse;
            

          } else if (event.type === 'error') {
            // Explicitly throw API errors to be caught by the outer catch or fall through
            throw new Error(event.message);
          }
        } catch (e) {
          // If the error we just threw is what we caught, re-throw it!
          if (e instanceof Error && e.message !== "Stream ended without result") { 
              // Differentiate between our intentional errors and random parse errors if possible
              // But simpler: checking if it matches the event.message format or logic
              if (line.includes('"type": "error"')) throw e;
          }
          console.warn("Error parsing or processing stream line:", line, e);
        }
      }
    }

    // Process any remaining buffer (if stream ended without final newline)
    if (buffer.trim()) {
        try {
            const event = JSON.parse(buffer);
            if (event.type === 'result') {
                finalResult = event.payload || event; // Handle potentially wrapped payload

            }
            else if (event.type === 'error') throw new Error(event.message);
        } catch (e) {
             console.warn("Error parsing final buffer:", buffer, e);
        }
    }
    
    if (!finalResult) {
        throw new Error("Stream ended without result");
    }

    return finalResult;
  } catch (error) {
    if (error instanceof Error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timed out.');
        }
        console.error('Chat API Error:', error.message);
    }
    throw error;
  } finally {
      clearTimeout(timeoutId);
  }
};

export const fetchCourses = async (): Promise<CourseName[]> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/courses`);
  if (!response.ok) {
    throw new Error('Failed to fetch courses');
  }
  return response.json();
};

export const addCourse = async (course: CourseName): Promise<void> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/courses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(course),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to add course');
  }
};

export const updateCourse = async (courseId: string, course: CourseName): Promise<void> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/courses/${courseId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(course),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to update course');
  }
};

export const deleteCourse = async (courseId: string): Promise<void> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/courses/${courseId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to delete course');
  }
};



export const submitReview = async (review: ReviewSubmission): Promise<void> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/v1/reviews`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(review),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to submit review');
  }
};



export const fetchReviews = async (courseId: string): Promise<Review[]> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/v1/reviews/${courseId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch reviews');
  }
  return response.json();
};

export const deleteReview = async (reviewId: number): Promise<void> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/v1/reviews/${reviewId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete review');
  }
};
export interface CourseSummary {
  course_id: string;
  summary: string | null;
  scores: {
    difficulty: number;
    workload: number;
    grading: number;
  };
  review_count: number;
  updated_at: string;
}

export const fetchSummary = async (courseId: string): Promise<CourseSummary> => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  const response = await fetch(`${baseUrl}/api/v1/summary/${courseId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch summary');
  }
  return response.json();
};
