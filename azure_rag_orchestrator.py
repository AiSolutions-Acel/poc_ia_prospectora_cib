from typing import List, Dict, Any, TypedDict
from langgraph.graph import END, StateGraph
from src.application.ports.output.llm_port import LlmPort
from src.application.ports.output.embedding_port import EmbeddingPort
from src.application.ports.output.vector_store_port import VectorStorePort
from src.providers.config import get_settings
from system_prompts import (
    SYSTEM_PROMPT_GENERATION_AZURE,
    SYSTEM_PROMPT_EVALUATE_RELEVANCE,
    SYSTEM_PROMPT_EVALUATE_HALLUCINATION,
    SYSTEM_PROMPT_EVALUATE_ANSWER,
    SYSTEM_PROMPT_REWRITE_QUERY,
    SYSTEM_PROMPT_ROUTE_INDEX,
)
import time

settings = get_settings()

class AzureAgentState(TypedDict):
    question: str
    query: str
    documents: List[Dict[str, Any]]
    generation: str
    retries: int
    logs: List[str]
    embedding_latency_ms: float
    search_latency_ms: float
    llm_latency_ms: float
    query_vector: List[float]
    index_name: str

class AzureRagOrchestrator:
    def __init__(self, llm_adapter: LlmPort, embedding_adapter: EmbeddingPort, vector_store_adapter: VectorStorePort):
        self.llm = llm_adapter
        self.embedding = embedding_adapter
        self.vector_store = vector_store_adapter

    def _grade_document_relevance(self, question: str, document_text: str) -> str:
        prompt = (
            f"Pregunta del usuario: {question}\n\n"
            f"Documento recuperado:\n{document_text}\n\n"
            "¿Es útil o relevante para la pregunta?"
        )
        return self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_EVALUATE_RELEVANCE).strip().lower()

    def _grade_hallucination(self, documents_text: str, generation: str) -> str:
        prompt = (
            f"Documentos de referencia:\n{documents_text}\n\n"
            f"Respuesta generada:\n{generation}\n\n"
            "¿La respuesta está totalmente respaldada y libre de alucinaciones?"
        )
        return self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_EVALUATE_HALLUCINATION).strip().lower()

    def _grade_answer(self, question: str, generation: str) -> str:
        prompt = (
            f"Pregunta del usuario: {question}\n\n"
            f"Respuesta generada:\n{generation}\n\n"
            "¿La respuesta responde de forma útil y directa a la pregunta?"
        )
        return self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_EVALUATE_ANSWER).strip().lower()

    def _rewrite_query(self, question: str) -> str:
        prompt = (
            f"Pregunta original: {question}\n\n"
            "Pregunta optimizada para búsqueda semántica:"
        )
        return self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_REWRITE_QUERY).strip()

    def _route_index(self, question: str) -> str:
        prompt = f"Pregunta del usuario: {question}\n\nÍndice elegido:"
        return self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_ROUTE_INDEX).strip()

    def build(self) -> StateGraph:
        workflow = StateGraph(AzureAgentState)

        def node_embed(state: AzureAgentState):
            query = state["query"]
            logs = list(state.get("logs", []))
            vector, latency = self.embedding.get_embedding(query)
            logs.append(f"[Azure] Embedding generado en {latency:.2f}ms para: '{query[:50]}...'")
            return {"query_vector": vector, "embedding_latency_ms": latency, "logs": logs}

        def node_route_index(state: AzureAgentState):
            question = state["question"]
            logs = list(state.get("logs", []))
            
            t0 = time.perf_counter()
            index_name = self._route_index(question)
            t1 = time.perf_counter()
            
            # Simple fallback if the LLM output is weird
            valid_indexes = ["idx-institucional", "idx-argumentario", "idx-oferta-academica", "idx-convenios"]
            if index_name not in valid_indexes:
                index_name = "idx-institucional"  # default fallback
                
            logs.append(f"[Router] Índice seleccionado: {index_name} en {(t1-t0)*1000:.2f}ms")
            return {"index_name": index_name, "logs": logs}

        def node_retrieve(state: AzureAgentState):
            query_vector = state["query_vector"]
            index_name = state.get("index_name", "idx-institucional")
            logs = list(state.get("logs", []))
            docs, latency = self.vector_store.retrieve(query_vector, index_name=index_name)
            logs.append(f"[S3 Vectors] Recuperados {len(docs)} documentos del índice '{index_name}' en {latency:.2f}ms")
            return {"documents": docs, "search_latency_ms": latency, "logs": logs}

        def node_grade_documents(state: AzureAgentState):
            question = state["question"]
            documents = state["documents"]
            logs = list(state.get("logs", []))
            relevant_docs = []
            for doc in documents:
                if self._grade_document_relevance(question, doc["text"]) == "si":
                    relevant_docs.append(doc)
            logs.append(f"Evaluador de Docs: {len(relevant_docs)} / {len(documents)} calificados como útiles.")
            return {"documents": relevant_docs, "logs": logs}

        def node_generate(state: AzureAgentState):
            question = state["question"]
            documents = state["documents"]
            logs = list(state.get("logs", []))
            
            if documents:
                context = "\n\n".join([d["text"] for d in documents])
                prompt = f"Información de referencia:\n{context}\n\nPregunta del usuario: {question}\n\nRespuesta:"
            else:
                prompt = question
            
            t0 = time.perf_counter()
            generation = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_GENERATION_AZURE)
            t1 = time.perf_counter()
            llm_latency = (t1 - t0) * 1000
            
            if not documents:
                logs.append(f"Sin documentos relevantes. El LLM respondió por su cuenta en {llm_latency:.2f}ms.")
            else:
                logs.append(f"[GPT-5.1] Respuesta generada con documentos en {llm_latency:.2f}ms.")
                
            return {"generation": generation, "llm_latency_ms": llm_latency, "logs": logs}

        def node_rewrite_query(state: AzureAgentState):
            query = state["query"]
            logs = list(state.get("logs", []))
            retries = state.get("retries", 0)
            new_query = self._rewrite_query(query)
            logs.append(f"Reescritura: '{query[:40]}...' → '{new_query[:40]}...' (Intento {retries + 1})")
            vector, emb_latency = self.embedding.get_embedding(new_query)
            logs.append(f"[Azure] Re-embedding generado en {emb_latency:.2f}ms")
            return {"query": new_query, "retries": retries + 1, "query_vector": vector, "logs": logs}

        def route_after_grading(state: AzureAgentState):
            if not state["documents"] and state.get("retries", 0) < settings.max_retries:
                return "rewrite"
            return "generate"

        def route_after_generation(state: AzureAgentState):
            if not state["documents"]:
                return "end"
            context = "\n\n".join([d["text"] for d in state["documents"]])
            if self._grade_hallucination(context, state["generation"]) == "no" and state.get("retries", 0) < settings.max_retries:
                return "rewrite"
            if self._grade_answer(state["question"], state["generation"]) == "no" and state.get("retries", 0) < settings.max_retries:
                return "rewrite"
            return "end"

        workflow.add_node("embed", node_embed)
        workflow.add_node("route_index", node_route_index)
        workflow.add_node("retrieve", node_retrieve)
        workflow.add_node("grade_documents", node_grade_documents)
        workflow.add_node("generate", node_generate)
        workflow.add_node("rewrite_query", node_rewrite_query)
        
        workflow.set_entry_point("embed")
        workflow.add_edge("embed", "route_index")
        workflow.add_edge("route_index", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges("grade_documents", route_after_grading, {"rewrite": "rewrite_query", "generate": "generate"})
        workflow.add_edge("rewrite_query", "retrieve")
        workflow.add_conditional_edges("generate", route_after_generation, {"rewrite": "rewrite_query", "end": END})

        return workflow.compile()
