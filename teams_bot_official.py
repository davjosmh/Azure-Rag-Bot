"""
Bot de Teams oficial siguiendo el patrón exacto de Microsoft que funciona
Basado en: https://learn.microsoft.com/en-us/azure/bot-service/skill-implement-consumer
"""

import asyncio
import sys
import traceback
import os
import logging
from http import HTTPStatus
from typing import Dict, List
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    TurnContext,
    ActivityHandler,
    MessageFactory
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes

# Agregar path para importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_chat_service import RagChatService


# OPCIÓN 1: Establecer variables de entorno directamente
os.environ["MicrosoftAppId"] = "92bc3ead-9f2c-4d71-a58e-2015571d3410"
os.environ["MicrosoftAppPassword"] = "QD-8Q~dQz5GzPx0UTmbeTp4GkLIRw1HSEPMYDcS4"

# Configurar logging en modo DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("teams_bot_official")

class Config:
    """Bot Configuration"""
    PORT = 3978
    APP_ID = "92bc3ead-9f2c-4d71-a58e-2015571d3410"
    APP_PASSWORD = "QD-8Q~dQz5GzPx0UTmbeTp4GkLIRw1HSEPMYDcS4"

# Create adapter using the official pattern
SETTINGS = ConfigurationBotFrameworkAuthentication(
    Config()  # Pass config object directly
)

STORAGE = MemoryStorage()
CONVERSATION_STATE = ConversationState(STORAGE)

# Create adapter with error handler (official pattern)

class AdapterWithErrorHandler(CloudAdapter):
    def __init__(self, settings: ConfigurationBotFrameworkAuthentication, config: Config, conversation_state: ConversationState):
        super().__init__(settings)
        self._conversation_state = conversation_state

        # Error handler
        async def on_error(context: TurnContext, error: Exception):
            logger.error(f"[on_turn_error] unhandled error: {error}")
            traceback.print_exc()

            # Send a message to the user
            await context.send_activity("The bot encountered an error or bug.")
            await context.send_activity("To continue to run this bot, please fix the bot source code.")

            # Clear out conversation state
            await self._conversation_state.delete(context)

        self.on_turn_error = on_error

ADAPTER = AdapterWithErrorHandler(SETTINGS, Config(), CONVERSATION_STATE)

# Create the Bot using ActivityHandler (official pattern)
class TeamsRAGBot(ActivityHandler):
    """Teams RAG Bot using official ActivityHandler pattern"""
    
    def __init__(self, conversation_state: ConversationState):
        super().__init__()
        self.conversation_state = conversation_state
        self.rag_service = RagChatService()

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle message activities"""
        try:
            user_message = turn_context.activity.text
            logger.debug(f"Received message: {user_message}")
            logger.debug(f"Activity: {turn_context.activity}")
            logger.debug(f"Headers: {getattr(turn_context, 'headers', 'N/A')}")

            # Use RAG service to get response
            rag_response = await self.rag_service.get_chat_completion(
                user_message=user_message,
                conversation_history=[]
            )

            # Send response
            response_text = rag_response.get("message", "Lo siento, no pude generar una respuesta.")
            logger.debug(f"RAG response: {response_text}")
            await turn_context.send_activity(MessageFactory.text(response_text))

        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}")
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text("Lo siento, ocurrió un error."))

    async def on_members_added_activity(self, members_added: List, turn_context: TurnContext):
        """Greet new members"""
        welcome_text = "¡Hola! Soy tu asistente RAG. ¿En qué puedo ayudarte?"
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def on_turn(self, turn_context: TurnContext):
        """Handle every turn of the bot and save state changes"""
        await super().on_turn(turn_context)
        # Save any state changes
        await self.conversation_state.save_changes(turn_context, False)

# Create the Bot
BOT = TeamsRAGBot(CONVERSATION_STATE)

# Main bot message handler (official pattern)
async def messages(req: Request) -> Response:
    """Main bot message handler - exact official pattern"""
    logger.debug(f"Incoming request headers: {dict(req.headers)}")
    # Check content type
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        logger.warning("Unsupported media type")
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    logger.debug(f"Incoming request body: {body}")
    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    try:
        # Official pattern: ADAPTER.process_activity(auth_header, activity, BOT.on_turn)
        invoke_response = await ADAPTER.process_activity(auth_header, activity, BOT.on_turn)
        if invoke_response:
            logger.debug(f"Invoke response: {invoke_response.body}")
            return json_response(data=invoke_response.body, status=invoke_response.status)
        logger.debug("No invoke response, returning 200 OK")
        return Response(status=HTTPStatus.OK)
    except Exception as e:
        logger.error(f"Error in messages endpoint: {e}")
        traceback.print_exc()
        return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

# Create app
APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        logger.info("Starting Teams RAG Bot...")
        logger.info(f"Bot ID: {Config.APP_ID}")
        web.run_app(APP, host="0.0.0.0", port=Config.PORT)
    except Exception as error:
        logger.exception("Fatal error running the bot:")
        raise error