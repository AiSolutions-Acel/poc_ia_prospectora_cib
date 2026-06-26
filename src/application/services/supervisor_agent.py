from typing import List, Dict, Any
import requests
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph_checkpoint_aws import DynamoDBSaver
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
        rag_subagent,
        mock_db: MockPrecioDb
    ):
        self.rag_subagent = rag_subagent
        self.mock_db = mock_db
        # Usando la tabla configurada en AWS us-east-2
        self.memory = DynamoDBSaver(
            table_name="cibertec_agent_checkpoints",
            region_name="us-east-2"
        )

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
                # Invocamos al sub-agente (Self-RAG)
                response = self.rag_subagent.invoke({
                    "question": query,
                    "query": query,
                    "retries": 0,
                    "logs": []
                })
                return response.get("generation", "No pude generar una respuesta.")
            except Exception as e:
                return f"Error al buscar información en la base de conocimientos: {str(e)}"

        @tool
        def consultar_precio_carrera(carrera_id: str, tipo_carrera_id: str = "", modalidad_id: str = "", sede_id: str = "") -> str:
            """
            Busca y devuelve el precio (matrícula y cuota mensual) de una carrera específica.
            Debes proporcionar obligatoriamente el ID de la carrera (carrera_id).
            Opcionalmente puedes filtrar por tipo_carrera_id, modalidad_id y sede_id.
            """
            try:
                params = {"carrera_id": carrera_id}
                if tipo_carrera_id: params["tipo_carrera_id"] = tipo_carrera_id
                if modalidad_id: params["modalidad_id"] = modalidad_id
                if sede_id: params["sede_id"] = sede_id

                url = settings.api_prices_url
                if not url.endswith("/precios"):
                    url = f"{url.rstrip('/')}/api/v1/precios"

                response = requests.get(url, params=params, timeout=10)
                
                # Manejar el 404 con un Fallback Inteligente
                if response.status_code == 404:
                    # Buscamos de forma más amplia (solo por carrera_id)
                    fallback_params = {"carrera_id": carrera_id}
                    fallback_res = requests.get(url, params=fallback_params, timeout=10)
                    
                    if fallback_res.status_code == 200:
                        fb_data = fallback_res.json()
                        fb_precios = fb_data.get("resultados", [])
                        if fb_precios:
                            sugerencia = (
                                f"Atención: La carrera con ID '{carrera_id}' NO se ofrece con esos filtros exactos.\n"
                                f"Pero SÍ se ofrece en las siguientes opciones:\n"
                            )
                            for p in fb_precios:
                                sugerencia += f"- [Modalidad ID: {p.get('modalidad_id')}] {p.get('modalidad')} | [Sede ID: {p.get('sede_id')}] {p.get('sede')}\n"
                            sugerencia += "Pídele al alumno que elija una de estas opciones reales."
                            return sugerencia
                    
                    return f"No se encontró la carrera con ID '{carrera_id}' bajo ningún formato."
                    
                response.raise_for_status()
                
                data = response.json()
                precios = data.get("resultados", [])

                if not precios:
                    return f"No se encontraron precios para la carrera con ID '{carrera_id}' con esos filtros. Por favor verifica los datos."
                
                resultado = "Cotizaciones encontradas:\n"
                for p in precios:
                    # Ajustamos los campos devueltos por la API (snake_case/camelCase depende de tu modelo)
                    c = p.get("carrera", "")
                    tc = p.get("tipo_carrera", "")
                    s = p.get("sede", "")
                    m = p.get("modalidad", "")
                    moneda = p.get("moneda", "S/.")
                    matr = p.get("matricula", 0.0)
                    cuota = p.get("cuota_mensual", 0.0)
                    brochure = p.get("brochure", "")

                    resultado += f"- {c} ({tc}) | Sede: {s} | Modalidad: {m} | Matrícula: {moneda} {matr} | Cuota: {moneda} {cuota}\n"
                    if brochure:
                        resultado += f"  Brochure: {brochure}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar la lista de precios vía API: {str(e)}"

        @tool
        def listar_carreras_disponibles(facultad_id: str = "", tipo_carrera_id: str = "", modalidad_id: str = "", sede_id: str = "") -> str:
            """
            Retorna la lista de carreras disponibles (ID y Nombre).
            Puedes filtrar opcionalmente proporcionando facultad_id, tipo_carrera_id, modalidad_id o sede_id.
            """
            try:
                url = settings.api_prices_url
                base_url = url.split("/api/v1")[0] + "/api/v1"
                
                params = {}
                if facultad_id: params["facultad_id"] = facultad_id
                if tipo_carrera_id: params["tipo_carrera_id"] = tipo_carrera_id
                if modalidad_id: params["modalidad_id"] = modalidad_id
                if sede_id: params["sede_id"] = sede_id

                response = requests.get(f"{base_url}/carreras", params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                carreras = data.get("carreras", [])
                
                if not carreras:
                    return "No hay carreras disponibles con esos filtros."

                resultado = "Carreras disponibles:\n"
                for c in carreras:
                    cid = c.get("id", "")
                    nombre = c.get("nombre", "")
                    tipo = c.get("tipo_carrera", "")
                    resultado += f"- [ID: {cid}] {nombre} ({tipo})\n"
                return resultado
            except Exception as e:
                return f"Error al consultar carreras: {str(e)}"

        @tool
        def listar_facultades_disponibles() -> str:
            """Retorna las facultades académicas disponibles en Cibertec."""
            try:
                url = settings.api_prices_url
                base_url = url.split("/api/v1")[0] + "/api/v1"
                response = requests.get(f"{base_url}/facultades", timeout=5)
                response.raise_for_status()
                data = response.json()
                
                resultado = "Facultades disponibles:\n"
                for f in data.get("facultades", []):
                    resultado += f"- [ID: {f.get('id')}] {f.get('nombre')}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar facultades: {str(e)}"

        @tool
        def listar_tipos_carrera_disponibles() -> str:
            """Retorna los tipos de carrera disponibles (ej. Técnica, Bachiller)."""
            try:
                url = settings.api_prices_url
                base_url = url.split("/api/v1")[0] + "/api/v1"
                response = requests.get(f"{base_url}/tipos-carrera", timeout=5)
                response.raise_for_status()
                data = response.json()
                
                resultado = "Tipos de carrera disponibles:\n"
                for t in data.get("tipos_carrera", []):
                    resultado += f"- [ID: {t.get('id')}] {t.get('nombre')}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar tipos de carrera: {str(e)}"

        @tool
        def listar_modalidades_disponibles() -> str:
            """Retorna las modalidades de estudio disponibles."""
            try:
                url = settings.api_prices_url
                base_url = url.split("/api/v1")[0] + "/api/v1"
                response = requests.get(f"{base_url}/modalidades", timeout=5)
                response.raise_for_status()
                data = response.json()
                
                resultado = "Modalidades disponibles:\n"
                for m in data.get("modalidades", []):
                    resultado += f"- [ID: {m.get('id')}] {m.get('nombre')}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar modalidades: {str(e)}"

        @tool
        def listar_sedes_disponibles() -> str:
            """Retorna las sedes disponibles en Cibertec."""
            try:
                url = settings.api_prices_url
                base_url = url.split("/api/v1")[0] + "/api/v1"
                
                response = requests.get(f"{base_url}/sedes", timeout=5)
                response.raise_for_status()
                resultado = "Sedes disponibles:\n"
                for s in data.get("sedes", []):
                    resultado += f"- [ID: {s.get('id')}] {s.get('nombre')}\n"
                return resultado
            except Exception as e:
                return f"Error al consultar sedes: {str(e)}"

        return [
            search_cibertec_info, 
            consultar_precio_carrera, 
            listar_carreras_disponibles, 
            listar_facultades_disponibles,
            listar_tipos_carrera_disponibles,
            listar_modalidades_disponibles,
            listar_sedes_disponibles
        ]

    def build(self):
        tools = self._build_tools()

        agent_executor = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=SYSTEM_PROMPT_ASESOR_COMERCIAL
        )

        return agent_executor
