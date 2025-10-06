"""
Teams Bot Implementation siguiendo patrones oficiales de Microsoft Bot Framework
"""
import traceback
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ChannelAccount
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_chat_service import RagChatService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeamsRAGBot(ActivityHandler):
    """
    Bot que implementa RAG para Microsoft Teams usando ActivityHandler oficial
    """
    
    def __init__(self):
        super().__init__()
        self.rag_service = RagChatService()
        logger.info("TeamsRAGBot initialized successfully")

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Maneja las actividades de mensaje siguiendo el patrón oficial de Microsoft
        """
        try:
            user_message = turn_context.activity.text
            logger.info(f"Received message: {user_message}")
            
            # Usar el servicio RAG para generar respuesta
            rag_response = await self.rag_service.get_chat_completion(
                user_message=user_message,
                conversation_history=[]  # Simplificado por ahora
            )
            
            # Enviar respuesta usando MessageFactory oficial
            response_text = rag_response.get("message", "Lo siento, no pude generar una respuesta.")
            response_activity = MessageFactory.text(response_text)
            
            await turn_context.send_activity(response_activity)
            logger.info("Response sent successfully")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Enviar mensaje de error amigable
            error_message = "Lo siento, ocurrió un error procesando tu mensaje. Por favor intenta de nuevo."
            await turn_context.send_activity(MessageFactory.text(error_message))

    async def on_members_added_activity(
        self, 
        members_added: list[ChannelAccount], 
        turn_context: TurnContext
    ):
        """
        Saluda a nuevos miembros que se unen a la conversación
        """
        welcome_text = (
            "¡Hola y bienvenido! 👋 "
            "Soy un bot de asistente con capacidades RAG. "
            "Puedo ayudarte a responder preguntas basadas en documentos. "
            "¡Pregúntame algo!"
        )
        
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))
                logger.info(f"Welcomed new member: {member.name}")

    async def on_turn(self, turn_context: TurnContext):
        """
        Override opcional del turn handler principal para logging adicional
        """
        try:
            logger.info(f"Processing activity type: {turn_context.activity.type}")
            await super().on_turn(turn_context)
        except Exception as e:
            logger.error(f"Error in on_turn: {str(e)}")
            logger.error(traceback.format_exc())
            # Re-raise para que el adaptador pueda manejarlo apropiadamente
            raise