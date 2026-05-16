import json
import logging
import sys
import os
# Ensure backend/ is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, Any, Optional

from llama_index.core import Settings
from core.config import summary_llm
from llama_index.core.llms import ChatMessage
from core.database import get_db_connection
from services.ingestion import ingest_summary_to_chroma

logger = logging.getLogger(__name__)

def get_course_reviews(course_id: str) -> list[str]:
    """Fetch all review contents for a given course."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT review_content FROM reviews WHERE course_id = %s", (course_id,))
        rows = cur.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        logger.error(f"Error fetching reviews for {course_id}: {e}")
        return []
    finally:
        if conn: conn.close()

def get_last_summary_info(course_id: str) -> Optional[Dict[str, Any]]:
    """Get info about the last summary for a course."""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT last_review_count FROM summary_reviews WHERE course_id = %s", (course_id,))
        row = cur.fetchone()
        if row:
            return {"last_review_count": row[0]}
        return None
    except Exception as e:
        logger.error(f"Error fetching summary info for {course_id}: {e}")
        return None
    finally:
        if conn: conn.close()

def update_summary_db(course_id: str, summary_data: dict, review_count: int):
    """Update SQL with new summary and scores."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        # Fetch additional info from courses table for sync
        cur.execute("""
            SELECT course_name_th, credits, faculty, category_64, competency_67 
            FROM courses WHERE course_id = %s
        """, (course_id,))
        course_row = cur.fetchone()
        
        c_name = course_row[0] if course_row else ""
        c_creds = course_row[1] if course_row else ""
        c_fac = course_row[2] if course_row else ""
        c_cat = course_row[3] if course_row else ""
        c_comp = course_row[4] if course_row else ""
        
        # Format text to Markdown for storage
        markdown_summary = (
            f"**เนื้อหาที่เรียน**:\n{summary_data.get('content', 'ไม่ระบุ')}\n\n"
            f"**รูปแบบการเรียนการสอน**:\n{summary_data.get('teaching_style', 'ไม่ระบุ')}\n\n"
            f"**การวัดผลและตัดเกรด**:\n{summary_data.get('assessment', 'ไม่ระบุ')}\n\n"
            f"**ข้อดี/ข้อควรระวัง**:\n{summary_data.get('pros_cons', 'ไม่ระบุ')}"
        )

        cur.execute("""
            INSERT INTO summary_reviews (
                course_id, summary_content, score_difficulty, score_workload, score_grading, 
                last_review_count, updated_at,
                course_name_th, credits, faculty, category_64, competency_67
            ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
            ON CONFLICT (course_id) DO UPDATE SET
                summary_content = EXCLUDED.summary_content,
                score_difficulty = EXCLUDED.score_difficulty,
                score_workload = EXCLUDED.score_workload,
                score_grading = EXCLUDED.score_grading,
                last_review_count = EXCLUDED.last_review_count,
                updated_at = CURRENT_TIMESTAMP,
                course_name_th = EXCLUDED.course_name_th,
                credits = EXCLUDED.credits,
                faculty = EXCLUDED.faculty,
                category_64 = EXCLUDED.category_64,
                competency_67 = EXCLUDED.competency_67;
        """, (
            course_id, 
            markdown_summary, 
            summary_data.get("difficulty", 0),
            summary_data.get("workload", 0),
            summary_data.get("grading", 0),
            review_count,
            c_name, c_creds, c_fac, c_cat, c_comp
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating summary DB for {course_id}: {e}")
        conn.rollback()
    finally:
        if conn: conn.close()

def generate_summary_llm(course_name: str, reviews: list[str]) -> Dict[str, Any]:
    """
    Generate summary and scores using LLM.
    Returns dict with aspect-based fields.
    """
    if not reviews:
        return {}

    reviews_text = "\n- ".join(reviews)
    
    prompt = f"""
    You are an expert course reviewer. Analyze the following student reviews for the course "{course_name}".
    
    Reviews:
    {reviews_text}
    
    **Task**: Return a JSON object with the following fields (summarize in Thai):
    1. "content": What topics are covered? (เนื้อหาที่เรียน)
    2. "teaching_style": Online/Onsite, strictness, atmosphere. (รูปแบบการเรียนการสอน)
    3. "assessment": Exams, homework, projects, grading criteria. (การวัดผลและตัดเกรด)
    4. "pros_cons": Key pros and cons explicitly mentioned. (ข้อดี/ข้อควรระวัง)
    5. Scores (0-3):
       - "difficulty" (0=No Info, 1=Easy, 2=Moderate, 3=Hard)
       - "workload" (0=No Info, 1=Light, 2=Moderate, 3=Heavy)
       - "grading" (0=No Info, 1=Easy A, 2=Fair, 3=Strict)

    **Constraints**:
    - Summarize objectively based ONLY on provided reviews.
    - If no info, say "ไม่มีข้อมูลในรีวิว".
    
    Output JSON ONLY.
    """
    
    try:
        llm = summary_llm
        response = llm.complete(prompt)
        text_resp = response.text.strip()
        
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        
        data = json.loads(text_resp.strip())
        return data
    except Exception as e:
        logger.error(f"LLM Summary Generation Error: {e}")
        return {
            "content": "ไม่สามารถสรุปข้อมูลได้",
            "teaching_style": "-",
            "assessment": "-",
            "pros_cons": "-",
            "difficulty": 0, "workload": 0, "grading": 0
        }


def check_and_summarize(course_id: str, course_name: str = "", force: bool = False):
    """
    Main entry point. Checks if summary update is needed and executes it.
    """
    logger.info(f"Checking summary for {course_id}...")
    
    reviews = get_course_reviews(course_id)
    current_count = len(reviews)
    
    if current_count == 0:
        logger.info(f"No reviews for {course_id}, skipping.")
        return

    last_info = get_last_summary_info(course_id)
    last_count = last_info["last_review_count"] if last_info else 0
    
    if force or (current_count - last_count >= 3) or (last_count == 0):
        print(f"Updating summary for {course_id} ({last_count} -> {current_count} reviews) [Force={force}]...")
        
        summary_data = generate_summary_llm(course_name, reviews)
        
        if summary_data.get("content"):
            update_summary_db(course_id, summary_data, current_count)
            
            # Helper logic to fetch freshly updated data for Ingestion
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT course_name_th, credits, faculty, category_64, competency_67, summary_content,
                               score_difficulty, score_workload, score_grading
                        FROM summary_reviews WHERE course_id = %s
                    """, (course_id,))
                    row = cur.fetchone()
                    
                    if row:
                        ingest_data = {
                            "course_id": course_id,
                            "course_name_th": row[0],
                            "credits": row[1],
                            "faculty": row[2],
                            "category_64": row[3],
                            "competency_67": row[4],
                            "summary_content": row[5], # This is now the Markdown formatted string
                            "score_difficulty": row[6],
                            "score_workload": row[7],
                            "score_grading": row[8]
                        }
                        
                        ingest_summary_to_chroma(ingest_data)
                        print(f"Summary for {course_id} updated successfully.")
                    
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"Error preparing ingestion data: {e}")
                    if conn: conn.close()
        else:
            print(f"Failed to generate summary for {course_id}.")
    else:
        logger.info(f"Summary for {course_id} is up to date.")
