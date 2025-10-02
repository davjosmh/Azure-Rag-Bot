import azure.functions as func
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext, MemoryStorage, ConversationState
from botbuilder.schema import Activity
import logging
import os
import json
from app.services.rag_chat_service import RagChatService

# Configuración del adaptador de Bot Framework
APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)

# Estado de conversación en memoria
memory = MemoryStorage()
conversation_state = ConversationState(memory)

# Instancia del servicio RAG
rag_service = RagChatService()

async def on_message_activity(turn_context: TurnContext):
    user_id = turn_context.activity.from_property.id
    text = turn_context.activity.text
    # Recuperar historial de la conversación
    conversation_data = await conversation_state.create_property("ConversationData").get(turn_context, {})
    chat_history = conversation_data.get("history", [])
    # Agregar el mensaje del usuario al historial
    chat_history.append({"role": "user", "content": text})
    # Llamar al servicio RAG (async)
    response = await rag_service.get_chat_completion([
        type("ChatMessage", (), msg)() for msg in chat_history
    ])
    # Extraer respuesta del modelo
    model_reply = response.choices[0].message.content if response and response.choices else "No response."
    # Agregar respuesta al historial
    chat_history.append({"role": "assistant", "content": model_reply})
    # Guardar historial actualizado
    conversation_data["history"] = chat_history
    await conversation_state.save_changes(turn_context)
    # Responder al usuario
    await turn_context.send_activity(model_reply)

async def messages_handler(req: func.HttpRequest) -> func.HttpResponse:
    if req.method != "POST":
        return func.HttpResponse("Método no permitido", status_code=405)
    body = req.get_body()
    activity = Activity().deserialize(json.loads(body))
    auth_header = req.headers.get("Authorization", "")
    try:
        response = await adapter.process_activity(activity, auth_header, on_message_activity)
        if response:
            return func.HttpResponse(json.dumps(response.body), mimetype="application/json", status_code=response.status)
        return func.HttpResponse("", status_code=201)
    except Exception as e:
        logging.exception("Error procesando actividad de bot")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    return await messages_handler(req)
