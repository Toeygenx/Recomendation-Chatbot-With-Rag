import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db_connection

def setup_summary_table():
    print("Setting up 'summary_reviews' table...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return

    try:
        cur = conn.cursor()
        
        # 1. Create table if not exists (Old Schema Base)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS summary_reviews (
                course_id VARCHAR(50) PRIMARY KEY,
                summary_content TEXT,
                score_difficulty INT,
                score_workload INT,
                score_grading INT,
                last_review_count INT DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Add New Columns (Safe Migration)
        new_columns = [
            ("course_name_th", "TEXT"),
            ("credits", "TEXT"),
            ("faculty", "TEXT"),
            ("category_64", "TEXT"),
            ("competency_67", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            try:
                cur.execute(f"ALTER TABLE summary_reviews ADD COLUMN {col_name} {col_type};")
                print(f"Added column: {col_name}")
            except Exception as e:
                # Ignore error if column already exists
                conn.rollback()
                pass
        
        # 3. Backfill Data from Courses Table
        print("Backfilling course details into summary_reviews from courses table...")
        cur.execute("""
            UPDATE summary_reviews s
            SET 
                course_name_th = c.course_name_th,
                credits = c.credits,
                faculty = c.faculty,
                category_64 = c.category_64,
                competency_67 = c.competency_67
            FROM courses c
            WHERE s.course_id = c.course_id;
        """)
        print(f"Backfill complete. Rows affected: {cur.rowcount}")
        
        conn.commit()
        cur.close()
        print("Table 'summary_reviews' updated successfully.")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    setup_summary_table()
