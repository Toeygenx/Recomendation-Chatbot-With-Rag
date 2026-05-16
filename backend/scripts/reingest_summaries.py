import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db_connection
from services.ingestion import ingest_summary_to_chroma, delete_from_chroma

def reingest_all_summaries():
    print("Starting manual re-ingestion of summaries from SQL...")
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return

    try:
        cur = conn.cursor()
        
        # 1. Fetch all summaries with full metadata
        print("Fetching summaries from SQL...")
        cur.execute("""
            SELECT 
                course_id, summary_content, 
                score_difficulty, score_workload, score_grading,
                course_name_th, credits, faculty, category_64, competency_67
            FROM summary_reviews
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} summaries to re-ingest.")
        
        # 2. Clear old summary vectors (Optional but safer to avoid duplicates strictly)
        # Note: ingest_summary_to_chroma uses unique ID f"summary_{course_id}", so upsert happens.
        # But we can explicit delete for cleanliness if we want.
        # delete_from_chroma({"type": "summary_review"}) 
        
        for r in rows:
            summary_data = {
                "course_id": r[0],
                "summary_content": r[1],
                "score_difficulty": r[2],
                "score_workload": r[3],
                "score_grading": r[4],
                "course_name_th": r[5],
                "credits": r[6],
                "faculty": r[7],
                "category_64": r[8],
                "competency_67": r[9]
            }
            
            if not summary_data["summary_content"]:
                continue
                
            ingest_summary_to_chroma(summary_data)
            
        print("Re-ingestion complete.")
        
    except Exception as e:
        print(f"Error re-ingesting summaries: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reingest_all_summaries()
