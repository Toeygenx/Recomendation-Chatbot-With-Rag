from llama_index.core.base.response.schema import Response
from models.schemas import QueryIntent, QueryCategory
import random 
from data.constants import SAMPLE_QUERIES

def handle_chit_chat(intent: QueryIntent, latency_data: dict) -> Response:

    chit_chat_response = (
    "**สวัสดีครับ! ผมคือผู้ช่วยอัจฉริยะสำหรับรายวิชาศึกษาทั่วไป (GenEd)** 🎓\n\n"
    "ผมพร้อมตอบทุกข้อสงสัย ทั้ง **ข้อมูลรายวิชา** และ **รีวิวจากรุ่นพี่** ครับ:\n\n"
    "1.  **ℹ️ ถามข้อมูล**: \"วิชาที่เรียนเกี่ยวกับดนตรี\", \"วิชา 01999033 เรียนเกี่ยวกับอะไร\"\n"
    "2.  **⭐ ถามรีวิว**: \"วิชา Arts of living ตัดเกรดยากไหม\", \"วิชาไหนเรียนสนุก\"\n\n"
    "*หมายเหตุ: ระบบตอบคำถามโดยอ้างอิงจากข้อมูลการรีวิว หากวิชาใดไม่มีรีวิวในเรื่องนั้นๆ ระบบอาจจะไม่สามารถให้คำตอบที่เฉพาะเจาะจงได้ครับ* 🙏\n\n"
    "*อยากรู้วิชาไหน พิมพ์ถามได้เลยครับ!* 👇"
)
    # chit_chat_response = (
    #     "**สวัสดีครับ! ผมคือผู้ช่วยอัจฉริยะสำหรับรายวิชาศึกษาทั่วไป (GenEd)** 🎓\n"
    #     "ผมสามารถช่วยคุณค้นหาข้อมูลได้ 7 ด้าน ดังนี้ครับ:\n\n"
    #     "1.  **ℹ️ ข้อมูลพื้นฐาน**: \"วิชา 01999033 คืออะไร\", \"หน่วยกิตวิชา Arts of living\"\n"
    #     "2.  **🏫 รูปแบบการสอน**: \"วิชา Arts of living เช็คชื่อไหม\", \"วิชาแบดมินตัน เรียนที่ไหน\"\n"
    #     "3.  **🔥 ความยากง่าย**: \"วิชาไทยศึกษา ตัดเกรดยากไหม\", \"วิชาศิลปะการดำเนินชีวิต เก็บ A ง่ายไหม\"\n"
    #     "4.  **⭐ รีวิวจากรุ่นพี่**: \"ขอรีวิววิชาการเป็นผู้ประกอบการ\", \"รุ่นพี่แนะนำอะไรเกี่ยวกับวิชาไทยศึกษาบ้าง\"\n"
    #     "5.  **💡 แนะนำรายวิชา**: \"แนะนำวิชาเกี่ยวกับดนตรี\", \"วิชาไหนเรียนสนุก\"\n"
    #     "6.  **🆚 เปรียบเทียบ**: \"เทียบวิชา 01355101 กับ 01355102 ให้หน่อย\"\n"
    #     "7.  **📂 ค้นหาตามหมวด**: \"ขอรายชื่อวิชาในหมวดอยู่ดีมีสุข\"\n\n"
    #     "*หมายเหตุ: ระบบตอบคำถามโดยอ้างอิงจากข้อมูลการรีวิว หากวิชาใดไม่มีรีวิวในเรื่องนั้นๆ ระบบอาจจะไม่สามารถให้คำตอบที่เฉพาะเจาะจงได้ครับ* 🙏\n\n"
    #     "*ลองพิมพ์คำถามที่คุณสงสัยมาได้เลยครับ!* 👇"
    # )
    # Pick random suggestions for engagement
    
    suggested_queries = random.sample(SAMPLE_QUERIES, min(3, len(SAMPLE_QUERIES)))

    return Response(
        response=chit_chat_response, 
        source_nodes=[],
        metadata={
            "intent": intent.dict(),    
            "latency_breakdown": latency_data,
            "suggested_queries": suggested_queries
        }
    )

def handle_unclear(intent: QueryIntent, latency_data: dict) -> Response:
    """
    Handle unclear queries with optional analysis and suggestions.
    """
    # Check if unclear analysis is available
    # Always try to provide suggestions if available (UnclearAnalyzer now guarantees them)
    suggested_queries = []
    
    # Default logic for off-topic/other
    response_text = "ขออภัยครับ ระบบไม่แน่ใจในคำถาม กรุณาลองระบุ **รหัสวิชา** หรือ **ชื่อวิชา** หรือถามให้ชัดเจนอีกครั้งครับ"

    if not suggested_queries:
        
        suggested_queries = random.sample(SAMPLE_QUERIES, min(3, len(SAMPLE_QUERIES)))

    return Response(
        response=response_text,
        source_nodes=[],
        metadata={
            "intent": intent.dict(), 
            "latency_breakdown": latency_data,
            "suggested_queries": suggested_queries
        }
    )

