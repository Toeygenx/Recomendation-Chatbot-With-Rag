import sys
import os

# Add parent directory to sys.path to allow imports from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from services.engine import UniversityRAG_Engine
from services.ingestion import ingest_course_by_data, ingest_review_by_data, delete_from_chroma
from models.schemas import ChatRequest, ChatResponse, SourceNode, CourseName, ReviewSubmission, Review
import psycopg2
from core.database import get_db_connection
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks # Added BackgroundTasks
from services.summary import check_and_summarize # Import summary service
# Global RAG Engine instance
rag_engine: UniversityRAG_Engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    Initializes the RAG Engine (loading models) on startup.
    """
    global rag_engine
    print("Initializing University RAG Engine...")
    try:
        rag_engine = UniversityRAG_Engine()
        print("RAG Engine Initialized Successfully.")
    except Exception as e:
        print(f"Failed to initialize RAG Engine: {e}")
        raise e
    
    yield
    
    print("Shutting down RAG Engine...")
    # Add any cleanup logic here if needed

app = FastAPI(
    title="University Course RAG API",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

# CORS (Adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_rag_engine():
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    return rag_engine

from fastapi.responses import StreamingResponse
import json

@app.post("/api/chat", response_model=ChatResponse)
async def chat_non_streaming(request: ChatRequest, engine: UniversityRAG_Engine = Depends(get_rag_engine)):
    """
    Non-streaming RAG Chat Endpoint.
    Returns a complete response with suggested queries for unclear cases.
    """
    try:
        # Use new Async Non-Streaming Method
        response = await engine.aquery(request.query)
        
        # Extract suggestions from top-level metadata (standardized)
        suggested_queries = response.metadata.get('suggested_queries', [])

        return ChatResponse(
            response=response.response,
            sources=[
                SourceNode(
                    node_id=node.node.node_id,
                    text=node.node.get_content(),
                    score=node.score,
                    metadata=node.node.metadata
                ) for node in (response.source_nodes or [])
            ],
            intent=response.metadata.get('intent'),
            latency_ms=response.metadata.get('latency_ms'),
            latency_breakdown=response.metadata.get('latency_breakdown'),
            suggested_queries=suggested_queries,
            debug_logs=response.metadata.get('debug_logs', [])
        )
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest, engine: UniversityRAG_Engine = Depends(get_rag_engine)):
    """
    RAG Chat Endpoint (Streaming).
    Returns a stream of JSON events:
    - {"type": "status", "message": "..."}
    - {"type": "token", "content": "..."}
    - {"type": "result", "payload": {...}}
    """
    
    async def event_generator():
        try:
             # Use the async generator from engine
             async for event in engine.stream_custom_query(request.query):
                 yield event
        except Exception as e:
             # Yield error event
             print(f"Streaming Error: {e}")
             yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "rag_engine": "ready" if rag_engine else "not_ready"}

@app.get("/api/courses", response_model=list[CourseName])
async def get_courses():
    """
    Get a list of all courses (ID and Thai Name only).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT course_id, course_name_th, category_64, competency_67, credits, faculty, doc_type, description, clos FROM courses ORDER BY course_id ASC;")
        rows = cur.fetchall()
        
        courses = []
        for r in rows:
            courses.append(CourseName(
                course_id=r[0], 
                course_name_th=r[1],
                category_64=r[2],
                competency_67=r[3],
                credits=r[4],
                faculty=r[5],
                doc_type=r[6],
                description=r[7],
                clos=r[8]
            ))
            
        cur.close()
        conn.close()
        return courses
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error fetching courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses")
async def add_course(course: CourseName):
    """
    Add a new course (and ingest to Chroma).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO courses (
            course_id, course_name_th, category_64, competency_67, credits, faculty, doc_type, description, clos
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            course.course_id,
            course.course_name_th,
            course.category_64,
            course.competency_67,
            course.credits,
            course.faculty,
            course.doc_type,
            course.description,
            course.clos
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Hook: Ingest to Chroma
        print(f"Hook: Ingesting course {course.course_id}...")
        ingest_course_by_data(course.dict())
        
        return {"message": "Course added successfully"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error adding course: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/courses/{course_id}")
async def update_course(course_id: str, course: CourseName):
    """
    Update an existing course (and re-ingest).
    Renaming Course ID is NOT supported by frontend, so we assume simple update.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        
        # Standard Update (same ID)
        update_query = """
        UPDATE courses SET
            course_name_th = %s,
            category_64 = %s,
            competency_67 = %s,
            credits = %s,
            faculty = %s,
            doc_type = %s,
            description = %s,
            clos = %s
        WHERE course_id = %s
        """
        
        cur.execute(update_query, (
            course.course_name_th,
            course.category_64,
            course.competency_67,
            course.credits,
            course.faculty,
            course.doc_type,
            course.description,
            course.clos,
            course_id
        ))
        
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Course not found")

        conn.commit()
        cur.close()
        conn.close()
        
        # Hook: Re-ingest
        # 1. Delete old Description (but keep Reviews!)
        print(f"Hook: Updating course {course_id}...")
        delete_from_chroma({"course_id": course_id, "type": "desc"})
        # 2. Ingest new Description
        ingest_course_by_data(course.dict())
        
        return {"message": "Course updated successfully"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error updating course: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str):
    """
    Delete a specific course by ID (and delete from Chroma).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Course not found")
            
        conn.commit()
        cur.close()
        conn.close()
        
        # Hook: Delete from Chroma (All types: desc and review)
        print(f"Hook: Deleting course {course_id} from Chroma...")
        delete_from_chroma({"course_id": course_id})
        
        return {"message": "Course deleted successfully"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error deleting course: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/summary/{course_id}")
async def get_course_summary(course_id: str):
    """
    Get the AI-generated summary and scores for a course.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT summary_content, score_difficulty, score_workload, score_grading, last_review_count, updated_at 
            FROM summary_reviews 
            WHERE course_id = %s
        """, (course_id,))
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if row:
            return {
                "course_id": course_id,
                "summary": row[0],
                "scores": {
                    "difficulty": row[1],
                    "workload": row[2],
                    "grading": row[3]
                },
                "review_count": row[4],
                "updated_at": row[5]
            }
        else:
            return {
                "course_id": course_id,
                "summary": None, 
                "scores": {"difficulty": 0, "workload": 0, "grading": 0},
                "message": "No summary generated yet"
            }
            
    except Exception as e:
        if conn: conn.close()
        print(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reviews")
async def submit_review(review: ReviewSubmission, background_tasks: BackgroundTasks):
    """
    Submit a review for a course (and ingest to Chroma).
    Triggers background summary update.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        
        # Updated to return ID
        insert_query = """
        INSERT INTO reviews (
            course_id, review_content, course_name, credits, faculty, category_64, competency_67
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        
        cur.execute(insert_query, (
            review.course_id,
            review.review_content,
            review.course_name,
            review.credits,
            review.faculty,
            review.category_64,
            review.competency_67
        ))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Hook: Ingest Review
        print(f"Hook: Ingesting review {new_id}...")
        review_data = review.dict()
        review_data['id'] = new_id
        ingest_review_by_data(review_data)
        
        # Hook: Check and Summarize (Background)
        print(f"Hook: Scheduling summary check for {review.course_id}...")
        background_tasks.add_task(check_and_summarize, review.course_id, review.course_name)
        
        return {"message": "Review submitted successfully"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error submitting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reviews/{course_id}", response_model=list[Review])
async def get_reviews(course_id: str):
    """
    Get all reviews for a specific course.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, course_id, course_name, review_content, credits, faculty, category_64, competency_67 FROM reviews WHERE course_id = %s ORDER BY id DESC", (course_id,))
        rows = cur.fetchall()
        
        reviews = []
        for r in rows:
            reviews.append(Review(
                id=r[0],
                course_id=r[1],
                course_name=r[2],
                review_content=r[3],
                credits=r[4],
                faculty=r[5],
                category_64=r[6],
                competency_67=r[7]
            ))
            
        cur.close()
        conn.close()
        return reviews
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/reviews/{review_id}")
async def delete_review(review_id: int, background_tasks: BackgroundTasks):
    """
    Delete a specific review by ID (and delete from Chroma).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    try:
        cur = conn.cursor()
        
        # Get course info before deletion for summary update
        cur.execute("SELECT course_id, course_name FROM reviews WHERE id = %s", (review_id,))
        review_data = cur.fetchone()
        
        if not review_data:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Review not found")
            
        course_id, course_name = review_data
        
        cur.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        # Rowcount check not strictly needed if fetchone succeeded, but logic stays effectively same for safety
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Review not found")
            
        conn.commit()
        cur.close()
        conn.close()
        
        # Hook: Delete Review from Chroma
        print(f"Hook: Deleting review {review_id} from Chroma...")
        delete_from_chroma({"review_id": review_id})
        
        # Trigger summary update
        print(f"Triggering summary update for {course_id}...")
        background_tasks.add_task(check_and_summarize, course_id, course_name, force=True)
        
        return {"message": "Review deleted successfully"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error deleting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
