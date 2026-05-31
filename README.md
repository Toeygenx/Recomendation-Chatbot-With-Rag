# Course Recomendation ChatBot 🎓🤖

**Course Recomendation ChatBot** คือระบบ AI แชทบอทอัจฉริยะที่ใช้สถาปัตยกรรม **RAG (Retrieval-Augmented Generation)** ในการช่วยนิสิตมหาวิทยาลัยค้นหา แนะนำ และให้ข้อมูลเกี่ยวกับรายวิชาศึกษาทั่วไป (GenEd) โดยผสมผสานข้อมูลรายละเอียดรายวิชาเข้ากับระบบการจัดการรีวิวจากผู้เรียนจริง

## 🌟 ฟีเจอร์หลัก (Key Features)

- **Intelligent RAG System**: นำเสนอคำตอบที่แม่นยำด้วยการใช้ข้อมูลจริงจากฐานข้อมูล (รายละเอียดวิชาและรีวิว) ผสมผสานกับการสร้างคำตอบที่เป็นธรรมชาติจาก LLM
- **Auto-Summarization Review**: ระบบจะรวบรวมรีวิวจากผู้ใช้และนำมาสรุปผลภาพรวมโดยอัตโนมัติด้วย LLM เพื่อช่วยลด Noise ก่อนนำไปใช้ในการค้นหา
- **Smart Query Routing**: วิเคราะห์เจตนาของผู้ใช้ (Intent) ว่าต้องการถามข้อมูลเจาะจงรายวิชา, ควานหารีวิว หรือให้ช่วยแนะนำรายวิชา เพื่อเลือกกลยุทธ์การค้นหาที่เหมาะสมที่สุด (Exact ID Match หรือ Semantic Search)
- **Advanced Retrieval**: ใช้เทคนิค Hybrid Search พร้อมระบบ Reranking เพื่อให้มั่นใจว่า Context ที่ได้ตรงกับความต้องการมากที่สุดก่อนส่งให้ LLM สร้างคำตอบ

## 🏗️ สถาปัตยกรรมระบบ (System Architecture)

ระบบถูกแบ่งออกเป็น 2 Pipeline หลัก:

1. **Offline Pipeline (Data Preparation)**:
   - นำเข้าข้อมูลรายวิชาและรีวิวลงสู่ฐานข้อมูล **PostgreSQL**
   - รัน Auto-Summarization เพื่อสรุปรีวิวรายวิชา
   - ทำ Data Embedding ด้วยโมเดล (เช่น `text-embedding-3-small`) แล้วเก็บลง **ChromaDB** แยกตามประเภทของข้อมูล

2. **Online Pipeline (Runtime RAG)**:
   - รับคำถามจาก User แล้วทำ Query Expansion
   - จำแนก Intent ของคำถามผ่าน Router
   - ค้นหาข้อมูล (Retrieve) จาก ChromaDB ตามกลยุทธ์ที่ได้จาก Router
   - จัดอันดับข้อมูลใหม่ (Rerank)
   - สังเคราะห์คำตอบสุดท้ายส่งกลับให้ User ผ่าน LLM Generator (เช่น Gemini / GPT-4o)

## 🛠️ เทคโนโลยีที่ใช้ (Tech Stack)

- **Backend**: Python
- **Database**: PostgreSQL (Relational Data), ChromaDB (Vector Store)
- **AI / LLM**: OpenAI / Google Gemini (สำหรับ Generation และ Summarization)
- **Infrastructure**: Docker, Docker Compose

## 🚀 การติดตั้งและใช้งาน (Getting Started)


### การรันระบบ Backend
เข้าไปที่โฟลเดอร์ `backend/` จากนั้นทำการติดตั้งไลบรารีและสร้าง Environment:
```bash
cd backend
pip install -r requirements.txt
```
ตั้งค่าไฟล์ `.env` สำหรับเชื่อมต่อ Database และใส่ API Keys 

**รันการสร้าง Database และ Ingest Data:**
```bash
# สร้างโครงสร้างตาราง
python scripts/setup_summary_db.py

# Ingest ข้อมูลเข้าสู่ SQL และ ChromaDB
python scripts/ingest.py
```

**เริ่มต้นรันระบบ Backend:**
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 3. การรันระบบ Frontend
เข้าไปที่โฟลเดอร์ `frontend/` จากนั้นทำการติดตั้งไลบรารีด้วย npm:
```bash
cd frontend
npm install
```
ตั้งค่าไฟล์ `.env`  

**เริ่มต้นรันระบบ Frontend:**
```bash
npm run dev
```
ระบบจะแสดง URL (โดยปกติคือ `http://localhost:8080` หรือ `http://localhost:5173`) ให้คุณเปิดเบราว์เซอร์เพื่อเริ่มใช้งานหน้าเว็บได้ทันที

## 📂 โครงสร้างโปรเจกต์ (Project Structure)
- `backend/` - โค้ดส่วนหลักที่จัดการ RAG, การเชื่อมต่อ Database และ API
- `frontend/` - โค้ดในส่วนของการแสดงผลและโต้ตอบกับผู้ใช้
