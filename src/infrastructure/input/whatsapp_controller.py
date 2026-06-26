from collections import deque
from pydantic import BaseModel
import logging
from fastapi import APIRouter, Query, Request, Response, HTTPException, BackgroundTasks

from src.providers.config import get_settings
from src.application.services.chat_use_case import ChatUseCase
from src.application.dto.chat_dto import ChatRequestDto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])
settings = get_settings()


class SendMessageRequest(BaseModel):
    phone_number: str
    message: str

# ──────────────────────────────────────────────
# GET /webhook — Verificación del Webhook (Meta)
# ──────────────────────────────────────────────


@router.get("")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta envía un GET con hub.mode, hub.verify_token y hub.challenge.
    Debemos devolver el challenge si el token coincide.
    """
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("✅ Webhook verificado correctamente.")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"⚠️ Verificación fallida. mode={mode}, token={token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.delete("/history/{phone_number}")
async def clear_history(phone_number: str):
    """
    Limpia el historial de LangGraph (memoria) para un número de teléfono específico.
    Esto permite probar el flujo desde cero (por ejemplo, para que vuelva a pedir los términos legales).
    """
    import boto3
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table = dynamodb.Table('cibertec_agent_checkpoints')

        # Hacemos un scan para buscar todos los items asociados a este número
        response = table.scan()
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        deleted_count = 0
        with table.batch_writer() as batch:
            for item in items:
                if phone_number in item['PK']:
                    batch.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
                    deleted_count += 1

        logger.info(
            f"🗑️ Historial borrado para {phone_number}: {deleted_count} registros eliminados.")
        return {"status": "ok", "message": f"Se eliminaron {deleted_count} registros de historial para {phone_number}"}
    except Exception as e:
        logger.error(f"Error limpiando historial: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", tags=["WhatsApp", "API"])
async def send_message_endpoint(req: SendMessageRequest):
    """
    Envía un mensaje de texto a un número de WhatsApp específico.
    Utiliza la API oficial de WhatsApp Cloud.
    """
    try:
        await _send_whatsapp_reply(req.phone_number, req.message)
        return {"status": "ok", "message": "Mensaje enviado exitosamente"}
    except Exception as e:
        logger.error(f"Error enviando mensaje manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# POST /webhook — Recibir mensajes de WhatsApp
# ──────────────────────────────────────────────

def get_chat_use_case() -> ChatUseCase:
    from main import chat_use_case
    return chat_use_case


# Caché circular para guardar los últimos 1000 IDs procesados (Idempotencia)
processed_message_ids = deque(maxlen=1000)


def _extract_message(body: dict) -> tuple[str | None, str | None, str | None]:
    """Extrae el número del remitente, el texto del mensaje y el ID del payload de Meta."""
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None, None, None

        msg = messages[0]
        sender = msg.get("from", "")
        msg_id = msg.get("id", "")

        # Soportar tanto texto plano como respuestas a botones interactivos
        if "text" in msg:
            text = msg["text"].get("body", "")
        elif "interactive" in msg:
            if msg["interactive"]["type"] == "button_reply":
                text = msg["interactive"]["button_reply"].get("title", "")
            elif msg["interactive"]["type"] == "list_reply":
                text = msg["interactive"]["list_reply"].get("title", "")
            elif msg["interactive"]["type"] == "nfm_reply":
                # NFM reply comes from WhatsApp Flows
                flow_response = msg["interactive"]["nfm_reply"].get(
                    "response_json", "{}")
                import json
                try:
                    data = json.loads(flow_response)
                    # Convertimos el JSON del formulario a texto para el Agente
                    text = "El usuario envió el formulario: " + \
                        ", ".join([f"{k}: {v}" for k, v in data.items()])
                except:
                    text = "El usuario envió un formulario."
            else:
                text = ""
        else:
            text = ""

        return sender, text, msg_id
    except (IndexError, KeyError):
        return None, None, None


@router.post("")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Recibe los mensajes entrantes de WhatsApp.
    Extrae el texto y lo procesa en background para responder de inmediato a Meta (evita reintentos por timeout).
    """
    body = await request.json()
    logger.info(f"📩 Webhook POST recibido: {body}")

    sender, text, msg_id = _extract_message(body)

    if not sender or not text or not msg_id:
        # Meta envía notificaciones de status (delivered, read) que no tienen texto.
        return {"status": "ok"}

    if msg_id in processed_message_ids:
        logger.info(
            f"⏭️ Mensaje duplicado ignorado (Idempotencia). ID: {msg_id}")
        return {"status": "ok"}

    # Guardar ID para no procesarlo de nuevo
    processed_message_ids.append(msg_id)

    # Enviar al background para no bloquear el retorno del webhook
    background_tasks.add_task(_process_message, sender, text)

    return {"status": "ok"}


async def _process_message(sender: str, text: str):
    """Lógica principal de procesamiento y envío delegada al background."""
    use_case = get_chat_use_case()
    chat_request = ChatRequestDto(session_id=sender, message=text)

    try:
        chat_response = use_case.execute(chat_request)
        answer = chat_response.answer

        # Parsear si el agente quiere enviar botones interactivos
        import re
        buttons_match = re.search(r"\[BOTONES:(.*?)\]", answer)
        form_match = re.search(r"\[FORMULARIO_INGRESO\]", answer)

        if buttons_match:
            options = [opt.strip() for opt in buttons_match.group(
                1).split("|") if opt.strip()]
            answer_text = answer[:buttons_match.start()].strip()
            # Enviar botones interactivos
            await _send_whatsapp_interactive(sender, answer_text, options)
        elif form_match:
            answer_text = answer.replace("[FORMULARIO_INGRESO]", "").strip()
            # Enviar Flow (Formulario)
            await _send_whatsapp_flow(sender, answer_text)
        else:
            # Enviar respuesta de texto normal
            await _send_whatsapp_reply(sender, answer)

    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}", exc_info=True)
        await _send_whatsapp_reply(
            sender,
            "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías repetirlo? 🙏"
        )


async def _send_whatsapp_reply(to: str, message: str):
    """Envía un mensaje de texto por la API de WhatsApp Cloud."""
    import httpx

    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(
                f"❌ Error enviando mensaje WhatsApp: {resp.status_code} - {resp.text}")
        else:
            logger.info(f"✅ Mensaje enviado a {to}")


async def _send_whatsapp_interactive(to: str, message: str, buttons: list[str]):
    """Envía un mensaje interactivo con botones por la API de WhatsApp Cloud."""
    import httpx

    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    # WhatsApp soporta hasta 3 botones por mensaje
    buttons = buttons[:3]
    buttons_payload = []
    for i, btn in enumerate(buttons):
        buttons_payload.append({
            "type": "reply",
            "reply": {
                "id": f"btn_{i}",
                # El título del botón no puede exceder 20 caracteres
                "title": btn[:20]
            }
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": message
            },
            "action": {
                "buttons": buttons_payload
            }
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(
                f"❌ Error enviando botones WhatsApp: {resp.status_code} - {resp.text}")
        else:
            logger.info(f"✅ Botones enviados a {to}")


async def _send_whatsapp_flow(to: str, message: str):
    """Envía un mensaje interactivo tipo Flow (Formulario) por la API de WhatsApp Cloud."""
    import httpx

    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "body": {
                "text": message if message else "Por favor completa el siguiente formulario:"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "mode": "draft",
                    "flow_message_version": "3",
                    "flow_token": "AQAAAAAAA",
                    "flow_id": "1196114015974800",  # El ID del Flow en Meta Business
                    "flow_cta": "Abrir Formulario",
                    "flow_action": "navigate",
                    "flow_action_payload": {
                        "screen": "FORMULARIO_INICIAL"  # El nombre de la pantalla en tu JSON del Flow
                    }
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(
                f"❌ Error enviando Flow WhatsApp: {resp.status_code} - {resp.text}")
        else:
            logger.info(f"✅ Flow enviado a {to}")
