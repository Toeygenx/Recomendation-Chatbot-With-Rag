from typing import List, Optional
import asyncio
import json
import time
import random
from data.constants import SAMPLE_QUERIES

from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.response_synthesizers import BaseSynthesizer, get_response_synthesizer
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.base.response.schema import Response
import chromadb
from core.config import (
    CHROMA_DB_DIR, CHROMA_COLLECTION, RERANK_MODE, TOP_K_RERANK, 
    rewrite_llm, rerank_llm 
)
from utils.monitor import reset_all_counters, print_performance_report
from services.router import OneShotRouter
from services.query_expander import QueryExpander
from models.schemas import QueryIntent, QueryCategory, ExpandedQuery, LogEntry
from prompts.templates import PROMPT_MAP

# Rerankers
from llama_index.core.postprocessor import LLMRerank
# from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank

from llama_index.core.bridge.pydantic import PrivateAttr

# New Components
from services.resolver import CourseResolver
from services.retriever import StrategyRetriever
from services.guardrails import handle_chit_chat, handle_unclear

class UniversityRAG_Engine(CustomQueryEngine):
    """
    Custom Query Engine for University Course RAG.
    Orchestrates: Expander -> Router -> SQL -> Retrieval Strategy -> Synthesis
    """
    retriever: BaseRetriever
    synthesizer: BaseSynthesizer
    router: OneShotRouter
    
    # Use PrivateAttr for internal state
    _vector_store: ChromaVectorStore = PrivateAttr()
    _index: VectorStoreIndex = PrivateAttr()
    # Components
    _resolver: CourseResolver = PrivateAttr()
    _strategy_retriever: StrategyRetriever = PrivateAttr()
    _reranker: object = PrivateAttr(default=None)
    _expander: QueryExpander = PrivateAttr()
    
    def __init__(self, **kwargs):
        # Initialize database
        db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        
        # Default components (interface requirements)
        retriever = index.as_retriever(similarity_top_k=5)
        synthesizer = get_response_synthesizer(response_mode="compact")
        router = OneShotRouter()
        
        super().__init__(retriever=retriever, synthesizer=synthesizer, router=router, **kwargs)
        self._vector_store = vector_store
        self._index = index
        
        # Init Sub-components
        self._resolver = CourseResolver()
        self._strategy_retriever = StrategyRetriever(index)
        self._expander = QueryExpander()
        
        # Init Reranker (Legacy SBERT support, but using LLM in Retriever now)
        # Keeping this if standalone reranking is needed, though Retriever handles it internally for some strats.
        # if RERANK_MODE == "sbert":
        #     self._reranker = SentenceTransformerRerank(
        #         model="BAAI/bge-reranker-base", 
        #         top_n=TOP_K_RERANK
        #     )
        # elif RERANK_MODE == "llm":
        #     self._reranker = LLMRerank(
        #         llm=rerank_llm,
        #         top_n=TOP_K_RERANK,
        #     )
        self._reranker = LLMRerank(
                llm=rerank_llm,
                top_n=TOP_K_RERANK,
            )

    def custom_query(self, query_str: str):
        # Legacy Sync Implementation - Redirect to Async runner manually if needed
        # But this method is required by CustomQueryEngine abstract base.
        # For this system, we primarily use stream_custom_query.
        # Minimal implementation for compatibility:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Use a non-streaming version (not fully implemented here as we focus on streaming)
        return Response(response="Non-streaming not fully supported in this refactor. Use streaming endpoint.", source_nodes=[])

    async def aquery(self, query_str: str):
        """
        Async Non-Streaming Query.
        Returns full response with logs and latency.
        """
        t_start = time.perf_counter()
        debug_logs = []
        
        # Helper for logging
        def add_log(step, details):
            entry = LogEntry(step=step, details=details, timestamp=time.perf_counter() - t_start)
            debug_logs.append(entry)
            # Console Log
            if isinstance(details, (dict, list)):
                print(f"[{step}]\n{json.dumps(details, ensure_ascii=False, indent=2)}")
            else:
                print(f"[{step}] {details}")
            return entry

        # 1. EXPAND
        print(f"\n--- New Query (Non-Stream): {query_str} ---")
        add_log("Input", query_str)
        
        t0 = time.perf_counter()
        expanded_data: ExpandedQuery = await asyncio.to_thread(self._expander.expand, query_str)
        t_expand = time.perf_counter() - t0
        add_log("Expansion", expanded_data.dict())

        # Unclear check
        if expanded_data.is_unclear:
            print(">> Query Flagged as Unclear by Expander")
            dummy_intent = QueryIntent(category=QueryCategory.UNCLEAR, reason="Expander flagged as unclear")
            resp = handle_unclear(dummy_intent, {})
            
            latency = (time.perf_counter() - t_start) * 1000
            print(f"[Latency] Total: {latency:.2f}ms")
            
            return Response(
                response=resp.response,
                source_nodes=[],
                metadata={
                    "intent": dummy_intent.dict(),
                    "suggested_queries": resp.metadata.get("suggested_queries", []),
                    "latency_ms": latency,
                    "debug_logs": [l.dict() for l in debug_logs]
                }
            )

        # 2. ROUTE
        print(">> Routing...")
        t0 = time.perf_counter()
        intent: QueryIntent = await asyncio.to_thread(self.router.route, expanded_data.expanded_query)
        t_route = time.perf_counter() - t0
        add_log("Routing", intent.dict())

        # Guardrails
        if intent.category == QueryCategory.CHIT_CHAT:
            print(">> ChitChat Detected")
            resp = handle_chit_chat(intent, {})
            return Response(
                response=resp.response,
                source_nodes=[],
                metadata={
                    "intent": intent.dict(),
                    "suggested_queries": resp.metadata.get("suggested_queries", []),
                    "latency_ms": (time.perf_counter() - t_start) * 1000,
                    "debug_logs": [l.dict() for l in debug_logs]
                }
            )

        if intent.category == QueryCategory.UNCLEAR:
            print(">> Unclear Intent Detected")
            resp = handle_unclear(intent, {})
            return Response(
                response=resp.response,
                source_nodes=[],
                metadata={
                    "intent": intent.dict(),
                    "suggested_queries": resp.metadata.get("suggested_queries", []),
                    "latency_ms": (time.perf_counter() - t_start) * 1000,
                    "debug_logs": [l.dict() for l in debug_logs]
                }
            )
            
        # 3. RESOLVE ID
        target_course_ids = []
        t_resolve = 0.0
        if intent.category in [QueryCategory.BASIC_INFO, QueryCategory.REVIEWS]:
            t0 = time.perf_counter()
            target_course_ids = await asyncio.to_thread(self._resolver.resolve_ids, intent)
            t_resolve = time.perf_counter() - t0
            add_log("Resolution", {"ids": target_course_ids})
            if target_course_ids:
                print(f">> Resolved IDs: {target_course_ids}")

        # 4. RETRIEVE
        print(f">> Retrieving (Strategy: {intent.category})...")
        t0 = time.perf_counter()
        nodes = await asyncio.to_thread(
            self._strategy_retriever.retrieve, 
            intent, expanded_data, target_course_ids
        )
        t_retrieve = time.perf_counter() - t0
        add_log("Retrieval", {"node_count": len(nodes), "top_score": nodes[0].score if nodes else 0})

        # 5. SYNTHESIZE
        print(f">> Synthesizing with {len(nodes)} context nodes...")
        t0 = time.perf_counter()
        
        if not nodes:
            # Fallback suggestions
            # Fallback suggestions
            fallback_suggestions = random.sample(SAMPLE_QUERIES, min(3, len(SAMPLE_QUERIES)))

            return Response(
                response=f"ขออภัยครับ ไม่พบข้อมูลที่เกี่ยวข้องกับ '{expanded_data.expanded_query}' ในระบบครับ",
                source_nodes=[],
                metadata={
                    "intent": intent.dict(),
                    "suggested_queries": fallback_suggestions,
                    "latency_ms": (time.perf_counter() - t_start) * 1000,
                    "debug_logs": [l.dict() for l in debug_logs]
                }
            )

        qa_template = PROMPT_MAP.get(intent.category.value, PROMPT_MAP["basic_info"])
        final_query = expanded_data.expanded_query
        
        # Non-streaming synthesis
        response_obj = await self.synthesizer.asynthesize(
            query=final_query,
            nodes=nodes,
            text_qa_template=qa_template
        )
        
        t_synth = time.perf_counter() - t0
        print(f">> Synthesis Complete ({t_synth:.2f}s)")
        add_log("Synthesis", {"response_length": len(response_obj.response)})

        latency_breakdown = {
            "expansion": float(f"{t_expand:.4f}"),
            "routing": float(f"{t_route:.4f}"),
            "resolution": float(f"{t_resolve:.4f}"),
            "retrieval": float(f"{t_retrieve:.4f}"),
            "synthesis": float(f"{t_synth:.4f}"),
            "total": float(f"{time.perf_counter() - t_start:.4f}")
        }
        print(f"\n[Latency Logs]\n{json.dumps(latency_breakdown, indent=2)}")

        # Return standard Response object but packed with our metadata
        return Response(
            response=response_obj.response,
            source_nodes=response_obj.source_nodes,
            metadata={
                "intent": intent.dict(),
                "latency_breakdown": latency_breakdown,
                "latency_ms": latency_breakdown["total"] * 1000,
                "debug_logs": [l.dict() for l in debug_logs]
            }
        )

    async def stream_custom_query(self, query_str: str):
        """
        Async Generator for Streaming Response (SSE).
        Yields: Status, Token, Result events.
        """
        t_start = time.perf_counter()
        debug_logs = []

        # Helper to yield structured events
        def pack_event(event_type, data):
            # Sanitize and Serialize
            def sanitize(obj):
                if isinstance(obj, float):
                    import math
                    if math.isnan(obj) or math.isinf(obj): return None
                    return obj
                if isinstance(obj, dict): return {k: sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list): return [sanitize(v) for v in obj]
                return obj
            
            clean = sanitize(data)
            return json.dumps({"type": event_type, **clean}, default=str, allow_nan=False) + "\n"

        def add_log(step, details):
            entry = LogEntry(step=step, details=details, timestamp=time.perf_counter() - t_start)
            debug_logs.append(entry)
            
            # Formatting for Console
            if isinstance(details, (dict, list)):
                formatted_details = json.dumps(details, ensure_ascii=False, indent=2)
                print(f"[{step}]\n{formatted_details}")
            else:
                print(f"[{step}] {details}")
                
            return pack_event("debug", entry.dict())

        # ---------------------------------------------------------
        # 1. EXPAND
        # ---------------------------------------------------------
        print(f"\n--- New Query: {query_str} ---") # <--- Log start
        yield pack_event("status", {"message": "กำลังวิเคราะห์และขยายความคำถาม..."})
        yield add_log("Input", query_str)
        
        t0 = time.perf_counter()
        expanded_data: ExpandedQuery = await asyncio.to_thread(self._expander.expand, query_str)
        t_expand = time.perf_counter() - t0
        
        yield add_log("Expansion", expanded_data.dict())
        
        # Check Expander Unclear Flag
        if expanded_data.is_unclear:
            print(">> Query Flagged as Unclear by Expander") # <--- Log
            yield pack_event("status", {"message": "คำถามไม่ชัดเจน..."})
            # Generate static unclear response
            dummy_intent = QueryIntent(category=QueryCategory.UNCLEAR, reason="Expander flagged as unclear")
            resp = handle_unclear(dummy_intent, {})
            
            latency = (time.perf_counter() - t_start) * 1000
            print(f"\n[Latency Logs (Unclear Expander)]\nExpansion: {t_expand:.4f}s\nTotal: {latency/1000:.4f}s")

            yield pack_event("result", {
                "response": resp.response, 
                "sources": [], 
                "intent": dummy_intent.dict(),
                "suggested_queries": resp.metadata.get("suggested_queries", []),
                "latency_ms": latency,
                "debug_logs": [l.dict() for l in debug_logs]
            })
            return

        # ---------------------------------------------------------
        # 2. ROUTE
        # ---------------------------------------------------------
        print(">> Routing...") # <--- Log
        yield pack_event("status", {"message": "กำลังจำแนก Intent (Router)..."})
        t0 = time.perf_counter()
        intent: QueryIntent = await asyncio.to_thread(self.router.route, expanded_data.expanded_query)
        t_route = time.perf_counter() - t0
        
        yield add_log("Routing", intent.dict())

        # Guardrails (ChitChat / Unclear from Router)
        if intent.category == QueryCategory.CHIT_CHAT:
             print(">> ChitChat Detected") # <--- Log
             resp = handle_chit_chat(intent, {})
             
             latency = (time.perf_counter() - t_start) * 1000
             print(f"\n[Latency Logs (ChitChat)]\nExpansion: {t_expand:.4f}s\nRouting: {t_route:.4f}s\nTotal: {latency/1000:.4f}s")
             
             yield pack_event("result", {
                 "response": resp.response, 
                 "sources": [], 
                 "intent": intent.dict(),
                 "suggested_queries": resp.metadata.get("suggested_queries", []),
                 "latency_ms": latency,
                 "debug_logs": [l.dict() for l in debug_logs]
             })
             return

        if intent.category == QueryCategory.UNCLEAR:
             print(">> Unclear Intent Detected")
             resp = handle_unclear(intent, {})
             
             latency = (time.perf_counter() - t_start) * 1000
             print(f"\n[Latency Logs (Unclear Router)]\nExpansion: {t_expand:.4f}s\nRouting: {t_route:.4f}s\nTotal: {latency/1000:.4f}s")

             yield pack_event("result", {
                 "response": resp.response, 
                 "sources": [], 
                 "intent": intent.dict(),
                 "suggested_queries": resp.metadata.get("suggested_queries", []),
                 "latency_ms": latency,
                 "debug_logs": [l.dict() for l in debug_logs]
             })
             return

        # ---------------------------------------------------------
        # 3. RESOLVE ID (If BasicInfo / Reviews)
        # ---------------------------------------------------------
        target_course_ids = []
        if intent.category in [QueryCategory.BASIC_INFO, QueryCategory.REVIEWS]:
            t0 = time.perf_counter()
            target_course_ids = await asyncio.to_thread(self._resolver.resolve_ids, intent)
            t_resolve = time.perf_counter() - t0
            yield add_log("Resolution", {"ids": target_course_ids})
            
            if target_course_ids:
                print(f">> Resolved IDs: {target_course_ids}") 
                yield pack_event("status", {"message": f"พบข้อมูลวิชา: {', '.join(target_course_ids)}"})
            else:
                 pass
        else:
            t_resolve = 0.0

        # ---------------------------------------------------------
        # 4. RETRIEVE (Strict Strategies)
        # ---------------------------------------------------------
        print(f">> Retrieving (Strategy: {intent.category})...") 
        yield pack_event("status", {"message": "กำลังค้นหาข้อมูล (Retrieving)..."})
        t0 = time.perf_counter()
        
        # Pass expanded_data to Retriever for Keywords & Filters
        nodes = await asyncio.to_thread(
            self._strategy_retriever.retrieve, 
            intent, 
            expanded_data, 
            target_course_ids
        )
        t_retrieve = time.perf_counter() - t0
        
        yield pack_event("status", {"message": f"พบข้อมูล {len(nodes)} รายการ"})
        yield add_log("Retrieval", {"node_count": len(nodes), "top_score": nodes[0].score if nodes else 0})

        # ---------------------------------------------------------
        # 5. SYNTHESIZE (Visual Thinking + Strict Answer)
        # ---------------------------------------------------------
        print(f">> Synthesizing with {len(nodes)} context nodes...") 
        yield pack_event("status", {"message": "กำลังเรียบเรียงคำตอบ (Synthesizing)..."})
        t0 = time.perf_counter()
        
        if not nodes:
            response_text = f"ขออภัยครับ ไม่พบข้อมูลที่เกี่ยวข้องกับ **'{query_str}'** ในระบบครับ"
            yield pack_event("token", {"content": response_text})
            
            # Fallback suggestions
            fallback_suggestions = random.sample(SAMPLE_QUERIES, min(3, len(SAMPLE_QUERIES)))
            
            yield pack_event("result", {
                "response": response_text,
                "sources": [],
                "intent": intent.dict(),
                "suggested_queries": fallback_suggestions,
                "latency_ms": (time.perf_counter() - t_start) * 1000,
                "debug_logs": [l.dict() for l in debug_logs]
            })
            return

        # Select Template
        # We use a custom query wrapper to force the "Reasoning + Answer" format
        qa_template = PROMPT_MAP.get(intent.category.value, PROMPT_MAP["basic_info"])
        
        # Use Expanded Query as the Question to ensure context focus
        final_query = expanded_data.expanded_query

        # Stream Synthesis
        stream_synthesizer = get_response_synthesizer(streaming=True, response_mode="compact")
        
        response_stream = await stream_synthesizer.asynthesize(
            query=final_query,
            nodes=nodes,
            text_qa_template=qa_template
        )
        
        full_response_text = ""
        async for text_chunk in response_stream.async_response_gen():
            full_response_text += text_chunk
            yield pack_event("token", {"content": text_chunk})
            
        t_synth = time.perf_counter() - t0
        print(f">> Synthesis Complete ({t_synth:.2f}s)") 
        
        # Extract Sources
        sources = []
        if hasattr(response_stream, "source_nodes"):
            for node in response_stream.source_nodes:
                if hasattr(node, "node"):
                     sources.append({
                        "node_id": node.node.node_id,
                         "text": node.node.text,
                         "score": node.score,
                         "metadata": node.node.metadata
                     })
        
        yield add_log("Synthesis", {"response_length": len(full_response_text)})

        latency_breakdown = {
            "expansion": float(f"{t_expand:.4f}"),
            "routing": float(f"{t_route:.4f}"),
            "resolution": float(f"{t_resolve:.4f}"),
            "retrieval": float(f"{t_retrieve:.4f}"),
            "synthesis": float(f"{t_synth:.4f}"),
            "total": float(f"{time.perf_counter() - t_start:.4f}")
        }

        print(f"\n[Latency Logs]\n{json.dumps(latency_breakdown, indent=2)}") 
        
        yield pack_event("result", {
            "response": full_response_text,
            "sources": sources,
            "intent": intent.dict(),
            "latency_ms": (time.perf_counter() - t_start) * 1000,
            "latency_breakdown": latency_breakdown,
            "debug_logs": [l.dict() for l in debug_logs]
        })
