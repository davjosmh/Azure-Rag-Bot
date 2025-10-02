from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import logging
import os
import json
from app.services.rag_chat_service import RagChatService
from starlette.status import HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED

app = FastAPI()

# Instancia del servicio RAG
rag_service = RagChatService()

# Historial de chat en memoria por usuario (simple, para demo)
user_histories = {}

@app.post("/api/messages")
async def messages(request: Request):
    if request.method != "POST":
        return Response("Método no permitido", status_code=HTTP_405_METHOD_NOT_ALLOWED)
    body = await request.json()
    # Extraer info básica del Activity
    user_id = body.get("from", {}).get("id", "anon")
    text = body.get("text", "")
    # Recuperar historial
    chat_history = user_histories.get(user_id, [])
    chat_history.append({"role": "user", "content": text})
    # Llamar a RAG (adaptar a modelo de ChatMessage)
    response = await rag_service.get_chat_completion([
        type("ChatMessage", (), msg)() for msg in chat_history
    ])
    model_reply = response.choices[0].message.content if response and response.choices else "No response."
    chat_history.append({"role": "assistant", "content": model_reply})
    user_histories[user_id] = chat_history
    # Responder en formato Activity
    reply = {
        "type": "message",
        "text": model_reply
    }
    return JSONResponse(content=reply, status_code=HTTP_201_CREATED)
