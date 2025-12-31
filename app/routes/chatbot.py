"""
Chatbot API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.services.chatbot_service import get_chatbot_service
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict] = None


class ChatResponse(BaseModel):
    response: str
    source: str
    confidence: float
    related_questions: List[str]
    faq_id: Optional[str] = None


class QuickSuggestion(BaseModel):
    text: str
    query: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_message: ChatMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the chatbot and get a response
    Uses hybrid approach: FAQ + Semantic Search + Gemini AI
    """
    try:
        chatbot = get_chatbot_service()
        
        # Build user context
        user_context = {
            "role": current_user.role,
            "user_id": str(current_user.id),
            "institution_id": str(current_user.institution_id) if current_user.institution_id else None,
            "institution_name": current_user.institution.name if current_user.institution else "RTS Platform"
        }
        
        # Merge with any additional context from request
        if chat_message.context:
            user_context.update(chat_message.context)
        
        # Get response
        result = chatbot.get_response(chat_message.message, user_context)
        
        return ChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {str(e)}"
        )


@router.get("/suggestions", response_model=List[QuickSuggestion])
async def get_suggestions(current_user: User = Depends(get_current_user)):
    """
    Get quick suggestion buttons for the chat interface
    """
    try:
        chatbot = get_chatbot_service()
        suggestions = chatbot.get_quick_suggestions()
        return [QuickSuggestion(**s) for s in suggestions]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting suggestions: {str(e)}"
        )


@router.get("/health")
async def chatbot_health():
    """
    Check chatbot service health and capabilities
    """
    try:
        chatbot = get_chatbot_service()
        return {
            "status": "healthy",
            "gemini_enabled": chatbot.gemini_enabled,
            "knowledge_base_loaded": len(chatbot.knowledge_base) > 0,
            "faq_count": len(chatbot._get_suggested_questions())
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Made with Bob
