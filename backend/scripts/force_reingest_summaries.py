import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db_connection
from services.ingestion import delete_from_chroma
from services.summary import check_and_summarize

def force_reingest_all():
    print("=== FORCE RE-INGEST SUMMARIES (SQL & Vector) ===")
    
    # 1. Clear Vector Store
    # The user requested to delete type='summary_review' first
    print("\n--- Step 1: Clearing Old Summaries from ChromaDB ---")
    delete_from_chroma({"type": "summary_review"})
    
    # 2. Fetch Courses
    print("\n--- Step 2: Fetching Courses with Reviews ---")
    conn = get_db_connection()
    if not conn:
        print("Database connection failed.")
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT r.course_id, c.course_name_th 
            FROM reviews r
            JOIN courses c ON r.course_id = c.course_id
        """)
        courses = cur.fetchall()
        print(f"Found {len(courses)} courses to process.")
        
        # 3. Regenerate & Ingest
        print("\n--- Step 3: Regenerating and Re-ingesting ---")
        for i, (c_id, c_name) in enumerate(courses, 1):
            print(f"[{i}/{len(courses)}] Processing {c_id} {c_name}...")
            # force=True causes:
            # - LLM generation (SQL Update)
            # - Ingest to Chroma (since check_and_summarize does ingestion internally if successful)
            check_and_summarize(c_id, course_name=c_name, force=True)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
    
    print("\n=== COMPLETE ===")

if __name__ == "__main__":
    force_reingest_all()
