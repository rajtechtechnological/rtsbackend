"""
WebSocket-based Chatbot Routes
Provides real-time streaming responses for better UX
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Optional
import json
from sqlalchemy.orm import joinedload
from app.services.chatbot_service import get_chatbot_service
from app.dependencies import get_current_user_ws
from app.models.user import User

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        # Don't call accept() here - the endpoint already accepts the connection
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    async def send_text(self, user_id: str, text: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(text)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat
    
    Client sends:
    {
        "type": "auth",
        "token": "jwt_token"
    }
    
    Then sends messages:
    {
        "type": "message",
        "message": "user question"
    }
    
    Server responds with:
    {
        "type": "response",
        "response": "answer",
        "source": "faq|gemini|fallback",
        "confidence": 0.95,
        "related_questions": [...],
        "faq_id": "optional"
    }
    
    Or for streaming (Gemini):
    {
        "type": "stream_start"
    }
    {
        "type": "stream_chunk",
        "chunk": "partial text"
    }
    {
        "type": "stream_end",
        "related_questions": [...]
    }
    """
    
    user_id = None
    user = None
    
    try:
        await websocket.accept()
        
        # Wait for authentication
        auth_data = await websocket.receive_json()
        
        if auth_data.get("type") != "auth":
            await websocket.send_json({
                "type": "error",
                "error": "Authentication required"
            })
            await websocket.close()
            return
        
        # Verify token and get user
        token = auth_data.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "error": "Token required"
            })
            await websocket.close()
            return
        
        # Authenticate user (simplified - you should use proper JWT verification)
        try:
            from jose import jwt
            from app.config import settings
            from app.database import SessionLocal
            
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            
            if not user_id:
                raise Exception("Invalid token")
            
            # Get user from database
            db = SessionLocal()
            # Eager load institution to avoid lazy loading issues after session close
            user = db.query(User).options(joinedload(User.institution)).filter(User.id == user_id).first()

            if not user:
                db.close()
                raise Exception("User not found")

            # Extract data while session is still open
            user_role = user.role
            user_id_str = str(user.id)
            institution_id_str = str(user.institution_id) if user.institution_id else None
            institution_name = user.institution.name if user.institution else "RTS Platform"
            db.close()

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "error": f"Authentication failed: {str(e)}"
            })
            await websocket.close()
            return

        # Connection established
        await manager.connect(websocket, user_id)
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to chatbot"
        })

        # Get chatbot service
        chatbot = get_chatbot_service()

        # Build user context (using extracted data)
        user_context = {
            "role": user_role,
            "user_id": user_id_str,
            "institution_id": institution_id_str,
            "institution_name": institution_name
        }
        
        # Message loop
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("message", "").strip()
                
                if not message:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Empty message"
                    })
                    continue
                
                try:
                    # Get response from chatbot
                    result = chatbot.get_response(message, user_context)
                    
                    # Send response for all source types
                    await websocket.send_json({
                        "type": "response",
                        "response": result["response"],
                        "source": result["source"],
                        "confidence": result["confidence"],
                        "related_questions": result.get("related_questions", []),
                        "faq_id": result.get("faq_id")
                    })
                
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Error processing message: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "error": "Unknown message type"
                })
    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(user_id)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/chat/stream")
async def websocket_chat_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint with streaming support for Gemini responses
    Provides character-by-character or chunk-by-chunk streaming
    """
    
    user_id = None
    user = None
    
    try:
        await websocket.accept()
        
        # Authentication (same as above)
        auth_data = await websocket.receive_json()
        
        if auth_data.get("type") != "auth":
            await websocket.send_json({
                "type": "error",
                "error": "Authentication required"
            })
            await websocket.close()
            return
        
        token = auth_data.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "error": "Token required"
            })
            await websocket.close()
            return
        
        # Authenticate (simplified)
        try:
            from jose import jwt
            from app.config import settings
            from app.database import SessionLocal
            
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            
            if not user_id:
                raise Exception("Invalid token")
            
            db = SessionLocal()
            # Eager load institution to avoid lazy loading issues after session close
            user = db.query(User).options(joinedload(User.institution)).filter(User.id == user_id).first()

            if not user:
                db.close()
                raise Exception("User not found")

            # Extract data while session is still open
            user_role = user.role
            user_id_str = str(user.id)
            institution_id_str = str(user.institution_id) if user.institution_id else None
            institution_name = user.institution.name if user.institution else "RTS Platform"
            db.close()

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "error": f"Authentication failed: {str(e)}"
            })
            await websocket.close()
            return

        await manager.connect(websocket, user_id)
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to streaming chatbot"
        })

        chatbot = get_chatbot_service()

        # Build user context (using extracted data)
        user_context = {
            "role": user_role,
            "user_id": user_id_str,
            "institution_id": institution_id_str,
            "institution_name": institution_name
        }
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("message", "").strip()
                
                if not message:
                    continue
                
                try:
                    result = chatbot.get_response(message, user_context)

                    # For Gemini, stream the response
                    if result["source"] == "gemini":
                        await websocket.send_json({"type": "stream_start"})

                        # Stream response word by word for better UX
                        response_text = result["response"]
                        words = response_text.split()

                        for i, word in enumerate(words):
                            chunk = word + (" " if i < len(words) - 1 else "")
                            await websocket.send_json({
                                "type": "stream_chunk",
                                "chunk": chunk
                            })
                            # Small delay for streaming effect (optional)
                            # await asyncio.sleep(0.05)

                        await websocket.send_json({
                            "type": "stream_end",
                            "related_questions": result.get("related_questions", [])
                        })
                    else:
                        # For FAQ, greeting, default - send immediately
                        await websocket.send_json({
                            "type": "response",
                            "response": result["response"],
                            "source": result["source"],
                            "confidence": result["confidence"],
                            "related_questions": result.get("related_questions", []),
                            "faq_id": result.get("faq_id")
                        })
                
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Error: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(user_id)
        try:
            await websocket.close()
        except:
            pass

# Made with Bob
