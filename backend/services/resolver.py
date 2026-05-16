from typing import List
from core.database import get_db_connection
from models.schemas import QueryIntent

class CourseResolver:
    def resolve_ids(self, intent: QueryIntent) -> List[str]:
        # Logic:
        # If course_codes present -> Use them directly (Bypass SQL)
        # If only course_names -> SQL Lookup
        # If neither -> Return empty (Semantic search only)
        
        extracted_ids = set()
        
        # 1. Direct Codes
        for code in intent.course_codes:
            # Basic cleaning if needed, e.g. remove spaces
            extracted_ids.add(code.strip())
            
        if extracted_ids:
            return list(extracted_ids)
            
        # 2. SQL Lookup for Names
        if intent.course_names:
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    for name in intent.course_names:
                        # Cleaning: Remove "วิชา" prefix if LLM missed it
                        name = name.replace("วิชา", "").replace("รายวิชา", "").strip()
                        
                        # Fuzzy match using pg_trgm (similarity) or ILIKE
                        # Using ILIKE for robustness on partial matches
                        cur.execute("""
                            SELECT course_id FROM courses 
                            WHERE course_name_th ILIKE %s OR course_name_en ILIKE %s
                            LIMIT 5
                        """, (f"%{name}%", f"%{name}%"))
                        rows = cur.fetchall()
                        for row in rows:
                            extracted_ids.add(row[0])
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"SQL Error: {e}")
        
        return list(extracted_ids)
