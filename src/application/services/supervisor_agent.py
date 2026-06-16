from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from openai import AzureOpenAI

from src.providers.config import get_settings
from system_prompts import SYSTEM_PROMPT_ASESOR_COMERCIAL
from src.application.ports.output.embedding_port import EmbeddingPort
from src.application.ports.output.vector_store_port import VectorStorePort
from mock_db import MockPrecioDb

settings = get_settings()


class SupervisorAgentOrchestrator:
    def __init__(
        self,
        embedding_adapter: EmbeddingPort,
        vector_store_adapter: VectorStorePort,
        mock_db: MockPrecioDb
    ):
        self.embedding = embedding_adapter
        self.vector_store = vector_store_adapter
        self.mock_db = mock_db
        self.memory = MemorySaver()

        # Azure OpenAI client compatible with LangChain Chat models
        # For create_react_agent we need a LangChain chat model.
        from langchain_openai import AzureChatOpenAI

        self.llm = AzureChatOpenAI(
            azure_deployment=settings.azure_llm_deployment,
            api_version=settings.azure_api_version,
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            temperature=0.2,  # Slight variation for conversational naturalness
        )

    def _build_tools(self):
        @tool
        def search_cibertec_info(query: str) -> str:
            """
            Busca información técnica, beneficios, becas, convenios y mallas curriculares de Cibertec en la base de conocimientos.
            Úsalo siempre que el usuario pregunte por detalles específicos de la institución.
            """
            try:
                vector, _ = self.embedding.get_embedding(query)
                docs, _ = self.vector_store.retrieve(vector)
                if not docs:
                    return "No se encontró información relevante en la base de conocimientos."

                context = "\n\n".join(
                    [f"Documento:\n{d['text']}" for d in docs])
                return f"Resultados de la búsqueda:\n{context}"
            except Exception as e:
                return f"Error al buscar información: {str(e)}"

        @tool
        def consultar_precio_carrera(carrera: str, tipo_carrera: str = "", modalidad: str = "", sede: str = "") -> str:
            """
            Busca y devuelve el precio (matrícula y cuota mensual) de una carrera específica.
            Debes proporcionar al menos el nombre de la carrera.
            Opcionalmente puedes filtrar por tipo_carrera (Técnica o Bachiller), modalidad (Presencial, Semipresencial, Online) y sede.
            Úsalo para consultar precios y elaborar una propuesta económica cuando tengas los datos del usuario.
            """
            try:
                precios = self.mock_db.buscar_cotizacion(carrera, tipo_carrera, modalidad, sede)
                if not precios:
                    return f"No se encontraron precios para la carrera '{carrera}' con esos filtros. Por favor verifica los datos."
                
                resultado = "Cotizaciones encontradas:\n"
                for p in precios:
                    resultado += f"- {p.carrera} ({p.tipo_carrera}) | Sede: {p.sede} | Modalidad: {p.modalidad} | Matrícula: {p.moneda} {p.matricula} | Cuota: {p.moneda} {p.cuota_mensual}\n"
                    if p.brochure:
                        resultado += f"  Brochure: {p.brochure}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar la lista de precios: {str(e)}"

        return [search_cibertec_info, consultar_precio_carrera]

    def build(self):
        tools = self._build_tools()

        agent_executor = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=SYSTEM_PROMPT_ASESOR_COMERCIAL
        )

        return agent_executor
