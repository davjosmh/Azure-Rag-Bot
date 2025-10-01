import azure.functions as func
import json
import asyncio
from app.services.rag_chat_service import rag_chat_service
from app.models.chat_models import ChatMessage

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        # Espera un array de mensajes, o solo la pregunta
        history = req_body.get("history")
        if not history:
            # Si solo viene una pregunta, crea el historial mínimo
            question = req_body.get("question")
            if not question:
                return func.HttpResponse("Missing 'question' or 'history'", status_code=400)
            history = [ChatMessage(role="user", content=question)]
        else:
            # Convierte el historial a objetos ChatMessage si es necesario
            history = [ChatMessage(**msg) if not isinstance(msg, ChatMessage) else msg for msg in history]

        # Ejecuta la función async de RAG
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(rag_chat_service.get_chat_completion(history))
        return func.HttpResponse(json.dumps(response.model_dump()), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
