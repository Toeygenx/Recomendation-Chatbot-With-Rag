
import sys
import os
import time

# Ensure backend/ is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db_connection
from services.summary import check_and_summarize

def get_all_courses_with_reviews():
    """Get list of (course_id, course_name_th) for all courses having reviews."""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT r.course_id, c.course_name_th 
            FROM reviews r
            JOIN courses c ON r.course_id = c.course_id
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return []
    finally:
        if conn: conn.close()

def main():
    print("Starting Summary Regeneration Process...")
    print("This will force LLM generation for ALL courses with reviews.")
    
    courses = get_all_courses_with_reviews()
    print(f"Found {len(courses)} courses to process.")
    
    for i, (cid, cname) in enumerate(courses):
        print(f"[{i+1}/{len(courses)}] Processing {cid} {cname}...")
        try:
            check_and_summarize(cid, cname, force=True)
            # Sleep briefly to avoid hitting rate limits too hard
            time.sleep(1)
        except Exception as e:
            print(f"Failed to process {cid}: {e}")
            
    print("\nRegeneration Complete!")

if __name__ == "__main__":
    main()
