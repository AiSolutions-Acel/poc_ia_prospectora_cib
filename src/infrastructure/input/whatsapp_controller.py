import logging
from fastapi import APIRouter, Query, Request, Response, HTTPException

from src.providers.config import get_settings
from src.application.services.chat_use_case import ChatUseCase
from src.application.dto.chat_dto import ChatRequestDto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])
settings = get_settings()


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


# ──────────────────────────────────────────────
# POST /webhook — Recibir mensajes de WhatsApp
# ──────────────────────────────────────────────

def get_chat_use_case() -> ChatUseCase:
    from main import chat_use_case
    return chat_use_case


def _extract_message(body: dict) -> tuple[str | None, str | None]:
    """Extrae el número del remitente y el texto del mensaje del payload de Meta."""
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None, None

        msg = messages[0]
        sender = msg.get("from", "")
        text = msg.get("text", {}).get("body", "")
        return sender, text
    except (IndexError, KeyError):
        return None, None


@router.post("")
async def receive_message(request: Request):
    """
    Recibe los mensajes entrantes de WhatsApp.
    Extrae el texto, lo pasa al Supervisor Agent y responde al usuario.
    """
    body = await request.json()
    logger.info(f"📩 Webhook POST recibido: {body}")

    sender, text = _extract_message(body)

    if not sender or not text:
        # Meta envía notificaciones de status (delivered, read) que no tienen texto.
        return {"status": "ok"}

    # Usar el número de teléfono como session_id para mantener la conversación
    use_case = get_chat_use_case()
    chat_request = ChatRequestDto(session_id=sender, message=text)

    try:
        chat_response = use_case.execute(chat_request)
        answer = chat_response.answer

        # Enviar respuesta por WhatsApp
        await _send_whatsapp_reply(sender, answer)

    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        await _send_whatsapp_reply(
            sender,
            "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías repetirlo? 🙏"
        )

    return {"status": "ok"}


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
            logger.error(f"❌ Error enviando mensaje WhatsApp: {resp.status_code} - {resp.text}")
        else:
            logger.info(f"✅ Mensaje enviado a {to}")
