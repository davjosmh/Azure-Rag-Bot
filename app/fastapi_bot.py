
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import logging
import os
import json
from app.services.rag_chat_service import RagChatService
from starlette.status import HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED
from jose import jwt
import httpx
from fastapi import status


app = FastAPI()

# Instancia del servicio RAG
rag_service = RagChatService()

# Historial de chat en memoria por usuario (simple, para demo)
user_histories = {}


async def validate_jwt_token(auth_header: str) -> bool:
    """
    Valida el JWT enviado por Teams/Bot Framework.
    Permite pruebas locales si no hay token.
    """
    if not auth_header:
        # Permitir pruebas locales sin token
        if os.environ.get("ALLOW_LOCAL_TESTS", "1") == "1":
            return True
        return False
    try:
        token = auth_header.split("Bearer ")[-1]
        # Obtener las claves públicas de Microsoft
        openid_config_url = "https://login.botframework.com/v1/.well-known/openidconfiguration"
        async with httpx.AsyncClient() as client:
            openid_config = (await client.get(openid_config_url)).json()
            jwks_uri = openid_config["jwks_uri"]
            jwks = (await client.get(jwks_uri)).json()
        # Decodificar y validar el token
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
        if not key:
            return False
        # Validar claims principales
        options = {"verify_aud": False}  # Puedes hacer más estricto si configuras el AppId
        payload = jwt.decode(token, key, algorithms=unverified_header["alg"], options=options)
        # Validar emisor
        if not payload.get("iss", "").startswith("https://api.botframework.com"):
            return False
        # Puedes agregar validación de "aud" aquí si quieres ser más estricto
        return True
    except Exception as e:
        logging.warning(f"Token JWT inválido: {e}")
        return False

@app.post("/api/messages")
async def messages(request: Request):
    # Validar JWT de Teams/Bot Framework
    auth_header = request.headers.get("Authorization", "")
    if not await validate_jwt_token(auth_header):
        return Response("Unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)

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
