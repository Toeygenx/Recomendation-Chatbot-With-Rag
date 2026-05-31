import os
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
import tiktoken
from llama_index.embeddings.openai import OpenAIEmbedding

# Load environment variables
load_dotenv()

# ---- CALLBACKS / TOKEN COUNTING ----
token_counter_main = TokenCountingHandler(tokenizer=tiktoken.get_encoding("cl100k_base").encode)
token_counter_rewrite = TokenCountingHandler(tokenizer=tiktoken.get_encoding("cl100k_base").encode)
token_counter_rerank = TokenCountingHandler(tokenizer=tiktoken.get_encoding("cl100k_base").encode)

# Global Settings (Synthesis)
Settings.callback_manager = CallbackManager([token_counter_main])

# ---- PATH / CONFIG ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up one level from core/
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chroma_db") or "/backend/chroma_db"
CHROMA_COLLECTION = "rag_courses"
print(f"Data Directory: {DATA_DIR}")
# Adjust source data dir logic if needed, but for now we assume we copy to DATA_DIR manually or via script
CSV_PATH_DESCRIPTION = os.path.join(DATA_DIR, "description.csv")
CSV_PATH_REVIEW = os.path.join(DATA_DIR, "review.csv")

# ---- LLM Configuration ----
# Main LLM for response generation
Settings.llm = OpenAILike(
    # model="openai/gpt-5-nano", #synth = 72.3646 s
    model="openai/gpt-4o-mini", #synth = 27.0892 s
    # model="openai/gpt-4.1-mini", #synth = 21.486 s    
    # model="openai/gpt-4.1-nano", #synth = 7.349 s   #ชอบตอบผิด format
    # model="x-ai/grok-4.1-fast",#use this for now
    # model="google/gemini-2.5-flash",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    is_chat_model=True,
    context_window=128000,
    system_prompt=(
        "คุณคือรุ่นพี่และที่ปรึกษาที่มีความรู้เกี่ยวกับวิชาศึกษาทั่วไป (GenEd) ของมหาวิทยาลัยเกษตรศาสตร์ "
        "หน้าที่ของคุณคือให้ข้อมูลที่ถูกต้องและเป็นประโยชน์แก่น้องๆ นิสิต โดยอาศัยข้อมูลที่มีให้เท่านั้น\n"
        "บุคลิกของคุณคือ: เป็นกันเอง สุภาพ มีความมั่นใจ และใช้คำลงท้ายแบบผู้ชาย ครับ เสมอ\n"
        
        "ข้อปฏิบัติสำคัญ (Critical Rules):\n"
        "1. **Strict Context Only**: ให้ตอบคำถามโดยใช้ข้อมูลจาก **Context** ที่ได้รับมาเท่านั้น ห้ามใช้ความรู้ภายนอกหรือแต่งเติมข้อมูลเองเด็ดขาด\n"
        "2. **Evidence-Based**: หากข้อมูลใน Context ไม่เพียงพอที่จะตอบคำถาม ให้แจ้งผู้ใช้ตามตรงว่า 'พี่ไม่พบข้อมูลในส่วนนี้ครับ' ห้ามมโนคำตอบ\n"
        "3. **ความถูกต้อง**: ตรวจสอบรหัสวิชา ชื่อวิชา และรายละเอียดให้ตรงกับ Context เสมอ\n"
        "4. **Persona**: พูดคุยด้วยภาษาที่เป็นกันเองเหมือนรุ่นพี่แนะนำรุ่นน้อง แต่ต้องอยู่บนพื้นฐานของข้อมูลจริงในระบบ\n"
        "5. **การคัดกรองเนื้อหาเชิงลบ**: ห้ามนำเสนอข้อมูลที่โจมตีบุคคล หรือสร้างภาพลักษณ์เสียหายแก่อาจารย์ผู้สอนหรือรายวิชาในเชิงลบที่รุนแรง หากพบข้อมูลเชิงลบที่รุนแรงใน Context ให้ข้ามข้อมูลส่วนนั้นไป\n"
        
        "รูปแบบการตอบ: ให้ใช้ **Markdown** ในการจัดรูปแบบคำตอบเสมอ\n"
        "   - ใช้หัวข้อ (##) แยกประเด็นสำคัญ\n"
        "   - ใช้รายการจุด (Bullet points) เพื่อให้อ่านง่าย\n"
        "   - ใช้ตัวหนา (**Bold**) เน้นรหัสวิชา, ชื่อวิชา, หรือประเด็นสำคัญ\n"
    ),
)

summary_llm = OpenAILike(
    model="x-ai/grok-4.1-fast",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    is_chat_model=True,
)

# Rewrite/Router LLM (Low latency preferred)
rewrite_llm = OpenAILike(
    # model="openai/gpt-4o-mini",    
    model="google/gemini-2.5-flash",
    # model="google/gemini-2.5-flash-lite",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    is_chat_model=True,
    callback_manager=CallbackManager([token_counter_rewrite])
)

# Rerank LLM (High precision preferred)
rerank_llm = OpenAILike(
    model="openai/gpt-4o-mini",    #rerank = 8.1567 s may be 10 s sometimes
    # model="google/gemini-2.5-flash",
    # model="openai/gpt-4o-mini",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    is_chat_model=True,
    callback_manager=CallbackManager([token_counter_rerank])
)

judge_llm = OpenAILike(
    model= "openai/gpt-4.1-mini",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    is_chat_model=True,
)

# ---- Embedding Configuration ----

# Settings.embed_model = HuggingFaceEmbedding(
#     model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
# )




# ---- Embedding Configuration ----
# Usage of OpenRouter for Embeddings
Settings.embed_model = OpenAIEmbedding(
    model_name="text-embedding-3-small", 
    api_base="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# ---- Chunking Configuration ----
Settings.chunk_size = 2048
Settings.chunk_overlap = 200

# ---- Rerank Configuration ----
# RERANK_MODE = "sbert" # Options: "sbert", "llm", or None    "rerank": 17.5009 s
RERANK_MODE = "llm" # Options: "sbert", "llm", or None

# ---- Top-K Configuration ----
TOP_K_RETRIEVAL = 30 # Initial top-k retrieval before reranking
TOP_K_RERANK = 6 # Final top-k after reranking     
