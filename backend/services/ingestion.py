import os
import shutil
import pandas as pd
import re
import chromadb
from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from core.config import (
    BASE_DIR, DATA_DIR, CSV_PATH_DESCRIPTION, CSV_PATH_REVIEW,
    CHROMA_DB_DIR, CHROMA_COLLECTION
)
from core.database import get_db_connection

SOURCE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "project_rag", "data")


def parse_course_name(full_name: str):
    """
    Extracts Thai and English names from a string like:
    'ผู้นำกับการพัฒนาภาคการเกษตร (Leaders and Agricultural Sectors Development)'
    Returns (name_th, name_en)
    """
    full_name = str(full_name).strip()
    match = re.search(r"^(.*?)\s*\(([^)]+)\)$", full_name)
    if match:
        name_th = match.group(1).strip()
        name_en = match.group(2).strip()
        return name_th, name_en
    else:
        return full_name, ""

def ingest_sql():
    print("Starting SQL Ingestion...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return
    
    try:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        
        # 1. Courses Table
        print("Recreating 'courses' table...")
        cur.execute("DROP TABLE IF EXISTS courses CASCADE;")
        cur.execute("""
            CREATE TABLE courses (
                course_id VARCHAR(50) PRIMARY KEY,
                course_name_th TEXT,
                course_name_en TEXT,
                category_64 TEXT,
                competency_67 TEXT,
                credits TEXT,
                faculty TEXT,
                doc_type TEXT,
                description TEXT,
                clos TEXT
            );
        """)
        
        # 2. Reviews Table
        print("Recreating 'reviews' table...")
        cur.execute("DROP TABLE IF EXISTS reviews;")
        cur.execute("""
            CREATE TABLE reviews (
                id SERIAL PRIMARY KEY,
                course_id VARCHAR(50),
                course_name TEXT,
                credits TEXT,
                faculty TEXT,
                category_64 TEXT,
                competency_67 TEXT,
                review_content TEXT,
                CONSTRAINT fk_course
                    FOREIGN KEY(course_id) 
                    REFERENCES courses(course_id)
                    ON DELETE CASCADE
            );
        """)
        
        # Ingest Courses
        if os.path.exists(CSV_PATH_DESCRIPTION):
            df = pd.read_csv(CSV_PATH_DESCRIPTION, dtype={'รหัสวิชา': str})
            print(f"Ingesting {len(df)} courses into SQL...")
            
            for _, row in df.iterrows():
                course_id = str(row['รหัสวิชา']).strip()
                full_name = str(row['ชื่อวิชา']).strip()
                name_th, name_en = parse_course_name(full_name)
                
                # Metadata
                cat_64 = str(row['กลุ่มสาระ - 64']) if pd.notna(row['กลุ่มสาระ - 64']) else ""
                comp_67 = str(row['สมรรถนะ - 67']) if pd.notna(row['สมรรถนะ - 67']) else ""
                credits = str(row['หน่วยกิต']) if pd.notna(row['หน่วยกิต']) else ""
                faculty = str(row['คณะต้นสังกัด']) if pd.notna(row['คณะต้นสังกัด']) else ""
                doc_type = str(row['doc_type']) if pd.notna(row['doc_type']) else ""
                description = str(row['description']) if pd.notna(row['description']) else ""
                clos = str(row['CLOs']) if pd.notna(row['CLOs']) else ""
                
                cur.execute(
                    """
                    INSERT INTO courses (
                        course_id, course_name_th, course_name_en, 
                        category_64, competency_67, credits, faculty,
                        doc_type, description, clos
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT (course_id) DO NOTHING;
                    """,
                    (course_id, name_th, name_en, cat_64, comp_67, credits, faculty, doc_type, description, clos)
                )
        else:
            print(f"Error: {CSV_PATH_DESCRIPTION} not found.")

        # Ingest Reviews
        if os.path.exists(CSV_PATH_REVIEW):
            df_review = pd.read_csv(CSV_PATH_REVIEW, dtype={'รหัสวิชา': str})
            print(f"Ingesting {len(df_review)} reviews into SQL...")
            
            for _, row in df_review.iterrows():
                course_id = str(row['รหัสวิชา']).strip()
                review_content = str(row['review']) if pd.notna(row.get('review')) else ""
                
                # Metadata (Duplicate from CSV for self-containment)
                course_name = str(row['ชื่อวิชา']).strip() if pd.notna(row.get('ชื่อวิชา')) else ""
                credits = str(row['หน่วยกิต']) if pd.notna(row.get('หน่วยกิต')) else ""
                faculty = str(row['คณะต้นสังกัด']) if pd.notna(row.get('คณะต้นสังกัด')) else ""
                cat_64 = str(row['กลุ่มสาระ - 64']) if pd.notna(row.get('กลุ่มสาระ - 64')) else ""
                comp_67 = str(row['สมรรถนะ - 67']) if pd.notna(row.get('สมรรถนะ - 67')) else ""

                if not review_content:
                    continue

                cur.execute(
                    """
                    INSERT INTO reviews (
                        course_id, course_name, credits, faculty, 
                        category_64, competency_67, review_content
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (course_id, course_name, credits, faculty, cat_64, comp_67, review_content)
                )

        conn.commit()
        cur.close()
        print(f"SQL Ingestion Complete.")
    except Exception as e:
        print(f"SQL Ingestion Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def format_doc_text(data_dict, text_col, meta_fields):
    """Prepend metadata to text content for better embedding context."""
    # Example format:
    # วิชา: ...
    # หน่วยกิต: ...
    # ...
    # รายละเอียด: <original text>
    
    meta_text = ""
    if 'course_id' in meta_fields:
        meta_text += f"รหัสวิชา: {meta_fields['course_id']}\n"
    if 'course_name' in meta_fields:
        meta_text += f"วิชา: {meta_fields['course_name']}\n"
    if 'credits' in meta_fields:
        meta_text += f"หน่วยกิต: {meta_fields['credits']}\n"
    if 'faculty' in meta_fields:
        meta_text += f"คณะ: {meta_fields['faculty']}\n"
    
    content = str(data_dict.get(text_col, "")) if data_dict.get(text_col) else "ไม่ระบุ"
    return f"{meta_text}เนื้อหา:\n{content}"

def ingest_chroma():
    print("Starting ChromaDB Ingestion (SQL Source)...")
    
    # Initialize Chroma Client
    db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # Reset collection
    try:
        db.delete_collection(CHROMA_COLLECTION)
        print(f"Deleted existing collection '{CHROMA_COLLECTION}'")
    except Exception as e:
        # Ignore if collection doesn't exist
        pass
        
    chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    docs = []
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for Chroma ingestion.")
        return

    try:
        cur = conn.cursor()
        
        # 1. Description Data (from courses table)
        print("Fetching courses from SQL...")
        cur.execute("""
            SELECT course_id, course_name_th, credits, faculty, category_64, competency_67, description 
            FROM courses
        """)
        rows = cur.fetchall()
        print(f"Processing {len(rows)} descriptions...")
        
        for r in rows:
            # Map tuple to dict
            row_dict = {
                "course_id": r[0],
                "course_name": r[1],
                "credits": r[2],
                "faculty": r[3],
                "category_64": r[4],
                "competency_67": r[5],
                "description": r[6]
            }
            
            # Metadata dict
            metadata = {
                "course_id": str(row_dict["course_id"]).strip(),
                "course_name": str(row_dict["course_name"]).strip(),
                "credits": str(row_dict["credits"]),
                "faculty": str(row_dict["faculty"]),
                "category_64": str(row_dict["category_64"]),
                "competency_67": str(row_dict["competency_67"]),
                "type": "desc"
            }
            
            # Clean metadata
            metadata = {k: v for k, v in metadata.items() if v and str(v).lower() != 'nan' and str(v).lower() != 'none'}
            
            # Prepare text
            text_content = format_doc_text(row_dict, 'description', metadata)
            
            docs.append(Document(text=text_content, metadata=metadata))

        # 2. Review Data (from reviews table)
        print("Fetching reviews from SQL...")
        cur.execute("""
            SELECT id, course_id, course_name, credits, faculty, category_64, competency_67, review_content 
            FROM reviews
        """)
        review_rows = cur.fetchall()
        print(f"Processing {len(review_rows)} reviews...")
        
        for r in review_rows:
            # Map tuple to dict
            row_dict = {
                "id": r[0],
                "course_id": r[1],
                "course_name": r[2],
                "credits": r[3],
                "faculty": r[4],
                "category_64": r[5],
                "competency_67": r[6],
                "review_content": r[7]
            }

            metadata = {
                "review_id": int(row_dict["id"]),  # Include review_id
                "course_id": str(row_dict["course_id"]).strip(),
                "course_name": str(row_dict["course_name"]).strip(),
                "credits": str(row_dict["credits"]),
                "faculty": str(row_dict["faculty"]),
                "category_64": str(row_dict["category_64"]),
                "competency_67": str(row_dict["competency_67"]),
                "type": "review"
            }
            
            # Clean metadata
            metadata = {k: v for k, v in metadata.items() if v and str(v).lower() != 'nan' and str(v).lower() != 'none'}
            
            text_content = format_doc_text(row_dict, 'review_content', metadata)

            docs.append(Document(text=text_content, metadata=metadata))

        cur.close()
        conn.close()

        if docs:
            print(f"Creating embeddings for {len(docs)} documents... (This may take a while)")
            VectorStoreIndex.from_documents(
                docs, storage_context=storage_context, show_progress=True
            )
            print("ChromaDB Ingestion Complete.")
        else:
            print("No documents found to ingest.")

    except Exception as e:
        print(f"Error during ChromaDB ingestion: {e}")
        if conn:
            conn.close()

# --- Real-time Sync Helpers ---

def get_chroma_collection():
    """Helper to get the Chroma collection object."""
    db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    return db.get_or_create_collection(CHROMA_COLLECTION)

def delete_from_chroma(where_filter: dict):
    """
    Delete documents from Chroma based on metadata filter.
    e.g., {'course_id': '01999033'} or {'review_id': 123}
    """
    try:
        collection = get_chroma_collection()
        collection.delete(where=where_filter)
        print(f"Deleted from Chroma: {where_filter}")
    except Exception as e:
        print(f"Error deleting from Chroma: {e}")

def ingest_course_by_data(course_data: dict):
    """
    Ingest a single course into ChromaDB.
    Expected dict keys: course_id, course_name_th, credits, faculty, category_64, competency_67, description
    """
    try:
        # Prepare Metadata
        metadata = {
            "course_id": str(course_data["course_id"]).strip(),
            "course_name": str(course_data.get("course_name_th", "")).strip(),
            "credits": str(course_data.get("credits", "")),
            "faculty": str(course_data.get("faculty", "")),
            "category_64": str(course_data.get("category_64", "")),
            "competency_67": str(course_data.get("competency_67", "")),
            "type": "desc"
        }
        # Clean metadata
        metadata = {k: v for k, v in metadata.items() if v and str(v).lower() != 'nan' and str(v).lower() != 'none'}
        
        # Prepare Text
        text_content = format_doc_text(
            {"description": course_data.get("description", "")}, 
            'description', 
            metadata
        )
        
        # Create Document
        doc = Document(text=text_content, metadata=metadata)
        
        # Upsert to Chroma
        print(f"Ingesting Course {metadata['course_id']} to Chroma...")
        chroma_collection = get_chroma_collection()
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        VectorStoreIndex.from_documents([doc], storage_context=storage_context)
        print("Course Ingestion Complete.")
        
    except Exception as e:
        print(f"Error ingesting course {course_data.get('course_id')}: {e}")

def ingest_review_by_data(review_data: dict):
    """
    Ingest a single review into ChromaDB.
    Expected dict keys: id, course_id, course_name, credits, faculty, category_64, competency_67, review_content
    """
    try:
        # Prepare Metadata
        metadata = {
            "review_id": int(review_data["id"]),
            "course_id": str(review_data["course_id"]).strip(),
            "course_name": str(review_data.get("course_name", "")).strip(),
            "credits": str(review_data.get("credits", "")),
            "faculty": str(review_data.get("faculty", "")),
            "category_64": str(review_data.get("category_64", "")),
            "competency_67": str(review_data.get("competency_67", "")),
            "type": "review"
        }
        # Clean metadata
        metadata = {k: v for k, v in metadata.items() if v and str(v).lower() != 'nan' and str(v).lower() != 'none'}
        
        # Prepare Text
        text_content = format_doc_text(
            {"review_content": review_data.get("review_content", "")}, 
            'review_content', 
            metadata
        )
        
        # Create Document
        doc = Document(text=text_content, metadata=metadata)
        
        # Upsert to Chroma
        print(f"Ingesting Review {metadata['review_id']} to Chroma...")
        chroma_collection = get_chroma_collection()
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        VectorStoreIndex.from_documents([doc], storage_context=storage_context)
        print("Review Ingestion Complete.")

    except Exception as e:
        print(f"Error ingesting review {review_data.get('id')}: {e}")

def ingest_summary_to_chroma(summary_data: dict):
    """
    Ingest a summary review into ChromaDB, mirroring review structure.
    Expected dict keys:
        - course_id, course_name_th (or course_name), credits, faculty, category_64, competency_67
        - summary_content
        - score_difficulty, score_workload, score_grading
    """
    try:
        # Prepare Metadata
        metadata = {
            "course_id": str(summary_data["course_id"]).strip(),
            "course_name": str(summary_data.get("course_name_th", summary_data.get("course_name", ""))).strip(),
            "credits": str(summary_data.get("credits", "")),
            "faculty": str(summary_data.get("faculty", "")),
            "category_64": str(summary_data.get("category_64", "")),
            "competency_67": str(summary_data.get("competency_67", "")),
            "type": "summary_review",
            "difficulty": int(summary_data.get("score_difficulty", 0)),
            "workload": int(summary_data.get("score_workload", 0)),
            "grading": int(summary_data.get("score_grading", 0))
        }
        
        # Clean metadata
        metadata = {k: v for k, v in metadata.items() if v is not None and str(v).lower() != 'nan' and str(v).lower() != 'none'}
        
        # Prepare Text
        text_content = format_doc_text(
            {"summary_content": summary_data.get("summary_content", "")}, 
            'summary_content', 
            metadata
        )
        
        # Create Document with specific ID to allow overwriting
        doc = Document(text=text_content, metadata=metadata)
        doc.id_ = f"summary_{metadata['course_id']}"
        
        # Upsert to Chroma
        print(f"Ingesting Summary {metadata['course_id']} to Chroma...")
        chroma_collection = get_chroma_collection()
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex.from_documents([doc], storage_context=storage_context)
        print("Summary Ingestion Complete.")

    except Exception as e:
        print(f"Error ingesting summary for {summary_data.get('course_id')}: {e}")
