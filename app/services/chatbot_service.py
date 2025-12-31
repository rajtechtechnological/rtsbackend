"""
Chatbot Service for RTS Platform
Hybrid approach: FAQ + Semantic Search + Gemini AI
"""

import os
from typing import Dict, List, Optional
from app.config_data.faq_config import search_faq, get_all_faqs
from app.config import settings

# Gemini will be optional - only used if API key is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai package not installed. Run: pip install google-generativeai")


class ChatbotService:
    def __init__(self):
        # Use settings from config.py which loads .env properly
        self.gemini_api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.gemini_enabled = GEMINI_AVAILABLE and bool(self.gemini_api_key)

        print(f"Chatbot init - Gemini available: {GEMINI_AVAILABLE}, API key set: {bool(self.gemini_api_key)}, Enabled: {self.gemini_enabled}")

        if self.gemini_enabled:
            genai.configure(api_key=self.gemini_api_key)
            # Use Gemini 2.0 Flash
            self.model = genai.GenerativeModel('gemini-3-flash-preview')
            print("Gemini model initialized: gemini-3-flash-preview")
        elif not GEMINI_AVAILABLE:
            print("To enable AI responses, install: pip install google-generativeai")

        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> str:
        """Load knowledge base from markdown file"""
        try:
            kb_path = os.path.join(os.path.dirname(__file__), '../../knowledge_base.md')
            with open(kb_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")
            return ""
    
    def get_response(
        self,
        message: str,
        user_context: Optional[Dict] = None
    ) -> Dict:
        """
        Get chatbot response using hybrid approach:
        1. Handle greetings directly
        2. Try FAQ matching first (fast, accurate)
        3. If no good match, use Gemini with knowledge base (flexible)
        4. If Gemini unavailable, return best FAQ match or fallback
        """

        # Step 0: Handle simple greetings
        greeting_response = self._handle_greeting(message)
        if greeting_response:
            return greeting_response

        # Step 1: Search FAQ database
        faq_results = search_faq(message, threshold=0.3)
        
        # If we have a high-confidence FAQ match, use it
        if faq_results and faq_results[0]["confidence"] >= 0.6:
            best_match = faq_results[0]["faq"]
            return {
                "response": best_match["answer"],
                "source": "faq",
                "confidence": faq_results[0]["confidence"],
                "faq_id": best_match["id"],
                "related_questions": self._get_related_questions(best_match)
            }
        
        # Step 2: If FAQ match is weak or none, try Gemini
        if self.gemini_enabled:
            try:
                print(f"Calling Gemini for message: {message[:50]}...")
                gemini_response = self._get_gemini_response(message, user_context, faq_results)
                print(f"Gemini response received: {len(gemini_response)} chars")
                return {
                    "response": gemini_response,
                    "source": "gemini",
                    "confidence": 0.8,
                    "related_questions": self._get_suggested_questions()
                }
            except Exception as e:
                import traceback
                print(f"Gemini error: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Fall through to FAQ fallback
        else:
            print(f"Gemini not enabled - falling back to FAQ/default")
        
        # Step 3: Fallback to best FAQ match or default response
        if faq_results:
            best_match = faq_results[0]["faq"]
            return {
                "response": f"I found this related information:\n\n{best_match['answer']}\n\nIf this doesn't answer your question, please try rephrasing or contact your institution support.",
                "source": "faq_fallback",
                "confidence": faq_results[0]["confidence"],
                "faq_id": best_match["id"],
                "related_questions": self._get_related_questions(best_match)
            }
        
        # No match at all
        return {
            "response": self._get_default_response(),
            "source": "default",
            "confidence": 0.0,
            "related_questions": self._get_suggested_questions()
        }
    
    def _get_gemini_response(
        self,
        message: str,
        user_context: Optional[Dict],
        faq_results: List
    ) -> str:
        """Get response from Gemini AI with context"""
        
        # Build context
        context_info = ""
        if user_context:
            role = user_context.get("role", "user")
            institution = user_context.get("institution_name", "your institution")
            context_info = f"\nUser Role: {role}\nInstitution: {institution}\n"
        
        # Include relevant FAQ context if available
        faq_context = ""
        if faq_results:
            faq_context = "\n\nPotentially relevant information:\n"
            for result in faq_results[:2]:  # Top 2 FAQs
                faq = result["faq"]
                faq_context += f"\nQ: {faq['question']}\nA: {faq['answer']}\n"
        
        # Build prompt
        prompt = f"""You are Raj, a friendly and helpful AI assistant for Rajtech Technological Systems (RTS), an education management platform.

{context_info}

Knowledge base about RTS platform:
{self.knowledge_base}

{faq_context}

User Question: {message}

Instructions:
- IMPORTANT: Detect the language of the user's question and respond in the SAME language
  - If user writes in Hindi, respond in Hindi
  - If user writes in English, respond in English
  - If user writes in any other language, respond in that language
- For questions about RTS platform (registration, courses, fees, exams, certificates), use the knowledge base above
- For general knowledge questions, answer them directly using your knowledge
- Be concise but complete
- Use a friendly, professional tone
- Format your response clearly with bullet points or numbered lists when appropriate

Answer:"""
        
        # Generate response
        response = self.model.generate_content(prompt)
        return response.text
    
    def _handle_greeting(self, message: str) -> Optional[Dict]:
        """Handle simple greetings and short messages"""
        msg_lower = message.lower().strip()

        # English greetings
        english_greetings = [
            "hi", "hello", "hey", "hii", "hiii", "hai", "helo",
            "good morning", "good afternoon", "good evening", "good night",
            "howdy", "sup", "what's up", "whats up", "wassup"
        ]

        # Hindi greetings
        hindi_greetings = ["namaste", "namaskar", "namasте", "pranam", "jai hind"]

        # Check for English greeting
        if msg_lower in english_greetings or any(msg_lower.startswith(g + " ") for g in english_greetings):
            return {
                "response": "Hello! I'm Raj, your AI assistant for Rajtech Technological Systems. How can I help you today?\n\nYou can ask me about:\n- Student registration\n- Available courses\n- Fee payments\n- Examinations\n- Certificates\n- And much more!",
                "source": "greeting",
                "confidence": 1.0,
                "related_questions": self._get_suggested_questions()
            }

        # Check for Hindi greeting
        if msg_lower in hindi_greetings or any(msg_lower.startswith(g + " ") for g in hindi_greetings):
            return {
                "response": "नमस्ते! मैं राज हूं, राजटेक टेक्नोलॉजिकल सिस्टम्स का AI सहायक। आज मैं आपकी कैसे मदद कर सकता हूं?\n\nआप मुझसे पूछ सकते हैं:\n- छात्र पंजीकरण\n- उपलब्ध कोर्स\n- फीस भुगतान\n- परीक्षाएं\n- प्रमाणपत्र\n- और भी बहुत कुछ!",
                "source": "greeting",
                "confidence": 1.0,
                "related_questions": self._get_suggested_questions()
            }

        # Handle thank you messages (English)
        thanks_en = ["thank you", "thanks", "thx", "ty", "thank u", "thankyou"]
        if msg_lower in thanks_en or any(t in msg_lower for t in thanks_en):
            return {
                "response": "You're welcome! Is there anything else I can help you with?",
                "source": "greeting",
                "confidence": 1.0,
                "related_questions": self._get_suggested_questions()
            }

        # Handle thank you messages (Hindi)
        thanks_hi = ["dhanyavad", "धन्यवाद", "shukriya", "शुक्रिया"]
        if msg_lower in thanks_hi or any(t in msg_lower for t in thanks_hi):
            return {
                "response": "आपका स्वागत है! क्या मैं आपकी और कोई मदद कर सकता हूं?",
                "source": "greeting",
                "confidence": 1.0,
                "related_questions": self._get_suggested_questions()
            }

        # Handle goodbye messages
        goodbyes = ["bye", "goodbye", "good bye", "see you", "cya", "take care", "alvida", "अलविदा"]
        if msg_lower in goodbyes or any(g in msg_lower for g in goodbyes):
            return {
                "response": "Goodbye! Feel free to come back if you have more questions. Have a great day!\n\nअलविदा! अगर आपके कोई सवाल हों तो वापस आएं। आपका दिन शुभ हो!",
                "source": "greeting",
                "confidence": 1.0,
                "related_questions": []
            }

        # Not a greeting
        return None

    def _get_related_questions(self, faq: Dict) -> List[str]:
        """Get related questions from the same category"""
        category = faq.get("category")
        if not category:
            return self._get_suggested_questions()
        
        all_faqs = get_all_faqs()
        related = [
            f["question"]
            for f in all_faqs
            if f.get("category") == category and f["id"] != faq["id"]
        ]
        return related[:3]  # Return top 3
    
    def _get_suggested_questions(self) -> List[str]:
        """Get general suggested questions"""
        return [
            "How do I register as a student?",
            "What courses are available?",
            "How do I pay my fees?",
            "How do exams work?",
            "How do I get my certificate?",
            "What can I see in my dashboard?"
        ]
    
    def _get_default_response(self) -> str:
        """Default response when no match found"""
        return """I'm Raj, your AI assistant for Rajtech Technological Systems!

I can help you with:
- Student registration and enrollment
- Course information
- Fee payments
- Examinations
- Certificates
- Dashboard features
- And more!

Please ask me a specific question, or try one of the suggested questions below.

For urgent matters or specific issues, please contact your institution's support staff."""

    def get_quick_suggestions(self) -> List[Dict]:
        """Get quick suggestion buttons for chat interface"""
        return [
            {
                "text": "How to register?",
                "query": "How do I register as a student?"
            },
            {
                "text": "Available courses",
                "query": "What courses are available?"
            },
            {
                "text": "Pay fees",
                "query": "How do I pay my fees?"
            },
            {
                "text": "Exam process",
                "query": "How do exams work?"
            },
            {
                "text": "Get certificate",
                "query": "How do I get my certificate?"
            }
        ]


# Singleton instance
_chatbot_service = None

def get_chatbot_service() -> ChatbotService:
    """Get or create chatbot service instance"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service

# Made with Bob
