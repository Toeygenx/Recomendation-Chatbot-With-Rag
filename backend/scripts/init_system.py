import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.setup_summary_db import setup_summary_table
from services.ingestion import ingest_sql, ingest_chroma
from services.summary import check_and_summarize
from core.database import get_db_connection

def batch_summarize_all():
    print("\nStarting Batch Summarization for all courses...")
    conn = get_db_connection()
    if not conn:
        print("DB Connection failed")
        return

    try:
        cur = conn.cursor()
        # Get all courses that have reviews
        cur.execute("""
            SELECT DISTINCT r.course_id, c.course_name_th 
            FROM reviews r
            JOIN courses c ON r.course_id = c.course_id
        """)
        courses = cur.fetchall()
        print(f"Found {len(courses)} courses with reviews to process.")
        
        for i, (c_id, c_name) in enumerate(courses, 1):
            print(f"[{i}/{len(courses)}] Processing {c_id} {c_name}...")
            # Forcing check_and_summarize. 
            # On first run, last_review_count is 0, so if reviews >= 3 it will run.
            check_and_summarize(c_id, course_name=c_name)
            
    except Exception as e:
        print(f"Error during batch summarization: {e}")
    finally:
        conn.close()

def main():
    print("=== GENED CHATBOT SYSTEM INITIALIZATION (SUMMARY ONLY) ===\n")
    
    # 1. Setup Database Schema (Summary Table)
    print("--- Step 1: Setting up Summary Table ---")
    # setup_summary_table()
    
    # 2. Ingest Raw Data (CSV -> SQL) - SKIPPED
    # print("\n--- Step 2: Ingesting Raw Data (CSV -> SQL) ---")
    # try:
    #     ingest_sql()
    # except Exception as e:
    #     print(f"Ingestion SQL failed: {e}")
    #     return

    # 3. Create Vectors (SQL -> Chroma) - SKIPPED
    # print("\n--- Step 3: Creating Vectors (SQL -> ChromaDB) ---")
    # try:
    #     ingest_chroma()
    # except Exception as e:
    #     print(f"Ingestion Chroma failed: {e}")
    #     return

    # 4. Generate Summaries (SQL Reviews -> LLM -> Summary SQL/Chroma)
    print("\n--- Step 2: Generating AI Summaries (New Tasks) ---")
    batch_summarize_all()
    # check_and_summarize("01999033", course_name="ศิลปะการดำเนินชีวิต Arts of Living")
    
    print("\n=== SUMMARY INITIALIZATION COMPLETE ===")

if __name__ == "__main__":
    main()
