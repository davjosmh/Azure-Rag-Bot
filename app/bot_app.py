"""
Flask Bot Application siguiendo patrones oficiales de Microsoft Bot Framework
"""
import asyncio
import traceback
from flask import Flask, request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, MessageFactory
from botbuilder.schema import Activity
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.teams_bot import TeamsRAGBot
from app.config import AppSettings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
settings = AppSettings()

# Microsoft Bot Framework credentials (hardcoded debido a problemas de .env)
MICROSOFT_APP_ID = "92bc3ead-9f2c-4d71-a58e-2015571d3410"
MICROSOFT_APP_PASSWORD = "QD-8Q~dQz5GzPx0UTmbeTp4GkLIRw1HSEPMYDcS4"

# Create Bot Framework Adapter Settings (configuración básica)
logger.info(f"Configurando BotFrameworkAdapter con App ID: {MICROSOFT_APP_ID}")
adapter_settings = BotFrameworkAdapterSettings(
    app_id=MICROSOFT_APP_ID,
    app_password=MICROSOFT_APP_PASSWORD
)

# Create Bot Framework Adapter
adapter = BotFrameworkAdapter(adapter_settings)
logger.info("BotFrameworkAdapter creado exitosamente")

# Create the Bot
bot = TeamsRAGBot()

# Error handler
async def on_error(context, error):
    """
    Error handler oficial recomendado por Microsoft
    """
    logger.error(f"Bot Framework error: {error}")
    logger.error(traceback.format_exc())
    
    try:
        # Send a message to the user
        await context.send_activity("Lo siento, ocurrió un error en el bot.")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")

# Set the error handler on the adapter
adapter.on_turn_error = on_error

@app.route("/api/messages", methods=["POST"])
def messages():
    """
    Main bot message endpoint siguiendo el patrón oficial de Microsoft
    """
    logger.info("=== NUEVO MENSAJE RECIBIDO ===")
    try:
        # Verify content type
        if "application/json" not in request.headers.get("Content-Type", ""):
            logger.warning("Invalid content type received")
            return Response(status=415)  # Unsupported Media Type
        
        # Get request body
        body = request.get_json()
        if not body:
            logger.warning("Empty request body")
            return Response(status=400)  # Bad Request
        
        logger.info(f"Activity type: {body.get('type', 'unknown')}")
        logger.info(f"From: {body.get('from', {}).get('name', 'unknown')}")
        
        # Create Activity from request body
        activity = Activity().deserialize(body)
        
        # Get Authorization header
        auth_header = request.headers.get("Authorization", "")
        logger.info(f"Auth header present: {'Yes' if auth_header else 'No'}")
        if auth_header:
            logger.info(f"Auth header starts with Bearer: {auth_header.startswith('Bearer ')}")
        
        # Usar el método más básico que evita parse_request completamente
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def simple_process():
                # Crear TurnContext directamente
                from botbuilder.core import TurnContext
                from botframework.connector.auth import ClaimsIdentity, AuthenticationConstants
                
                # Create ClaimsIdentity for authentication
                claims_identity = ClaimsIdentity({
                    AuthenticationConstants.AUDIENCE_CLAIM: MICROSOFT_APP_ID,
                    AuthenticationConstants.APP_ID_CLAIM: MICROSOFT_APP_ID,
                    AuthenticationConstants.VERSION_CLAIM: "1.0"
                }, True)
                
                # Create TurnContext
                context = TurnContext(adapter, activity)
                context.turn_state[adapter.BOT_IDENTITY_KEY] = claims_identity
                
                # Run bot logic
                await bot.on_turn(context)
                return None
            
            invoke_response = loop.run_until_complete(simple_process())
            
            if invoke_response:
                return Response(
                    response=json.dumps(invoke_response.body) if invoke_response.body else "",
                    status=invoke_response.status,
                    headers={"Content-Type": "application/json"}
                )
            else:
                return Response(status=200)
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in messages endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return Response(status=500)

@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint
    """
    return {"status": "healthy", "bot": "Teams RAG Bot"}, 200

@app.route("/", methods=["GET"])
def home():
    """
    Home endpoint with bot information
    """
    return {
        "message": "Teams RAG Bot is running",
        "framework": "Microsoft Bot Framework v4",
        "endpoints": {
            "messages": "/api/messages",
            "health": "/health"
        }
    }, 200

if __name__ == "__main__":
    logger.info("Starting Teams RAG Bot...")
    logger.info(f"Bot ID: {MICROSOFT_APP_ID}")
    logger.info(f"Bot Password length: {len(MICROSOFT_APP_PASSWORD)} characters")
    
    try:
        app.run(
            host="0.0.0.0",
            port=3978,
            debug=False  # Set to False in production
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise