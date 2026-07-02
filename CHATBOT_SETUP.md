# RTS Chatbot Setup Guide

## Overview

The RTS Chatbot uses a **hybrid approach** for intelligent responses:

1. **FAQ System** (Primary) - Fast, accurate responses for common questions
2. **Semantic Search** - Matches user questions to similar FAQs
3. **Gemini Flash 2.0** (Optional) - Handles complex queries using knowledge base

## Features

✅ **Predefined Q&A** - 20+ common questions with accurate answers
✅ **Smart Matching** - Handles question variations and synonyms
✅ **Context-Aware** - Uses user role and institution context
✅ **Related Questions** - Suggests follow-up questions
✅ **Fallback System** - Works even without Gemini API
✅ **Real-time Responses** - Fast FAQ responses, AI for complex queries

## Installation

### 1. Install Dependencies

```bash
cd rtsbackend

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install google-generativeai

# Update requirements.txt
pip freeze > requirements.txt
```

### 2. Get Gemini API Key (Optional but Recommended)

1. Visit https://ai.google.dev/
2. Sign in with Google account
3. Go to "Get API Key"
4. Create new API key
5. Copy the key

### 3. Configure Environment

Add to your `.env` file:

```env
# Gemini API (Optional - chatbot works without it using FAQ only)
GEMINI_API_KEY=your_gemini_api_key_here
```

**Note:** If you don't set `GEMINI_API_KEY`, the chatbot will still work using the FAQ system only.

### 4. Verify Setup

Start the backend server:

```bash
uvicorn app.main:app --reload
```

Test the chatbot health endpoint:

```bash
curl http://localhost:8000/api/chatbot/health
```

Expected response:
```json
{
  "status": "healthy",
  "gemini_enabled": true,  // or false if no API key
  "knowledge_base_loaded": true,
  "faq_count": 6
}
```

## How It Works

### Request Flow

1. **User sends message** → Frontend ChatWidget
2. **API receives message** → `/api/chatbot/chat` endpoint
3. **FAQ Search** → Searches predefined Q&A database
4. **High confidence match?**
   - YES → Return FAQ answer immediately
   - NO → Continue to step 5
5. **Gemini available?**
   - YES → Use Gemini with knowledge base context
   - NO → Return best FAQ match or default response
6. **Response sent** → With related questions

### Response Sources

- `faq` - Direct FAQ match (confidence ≥ 0.6)
- `gemini` - AI-generated response using knowledge base
- `faq_fallback` - Best FAQ match when confidence < 0.6
- `default` - No match found, general help message

## FAQ Database

Located in: `app/config/faq_config.py`

### Categories

- **registration** - Student enrollment process
- **courses** - Available courses and details
- **payments** - Fee payment process
- **exams** - Examination system
- **certificates** - Certificate generation
- **attendance** - Attendance tracking
- **login** - Login and access issues
- **dashboard** - Dashboard features
- **roles** - User roles and permissions
- **support** - Getting help
- **progress** - Progress tracking

### Adding New FAQs

Edit `app/config/faq_config.py`:

```python
{
    "id": "unique_id",
    "category": "category_name",
    "question": "Main question text",
    "variations": [
        "alternative phrasing 1",
        "alternative phrasing 2",
    ],
    "answer": """Your detailed answer here.
    
    Can include:
    - Bullet points
    - Multiple paragraphs
    - Step-by-step instructions
    """
}
```

## Knowledge Base

Located in: `rtsbackend/knowledge_base.md`

This markdown file contains comprehensive information about:
- Organization structure
- User roles and permissions
- Student registration process
- Course details
- Payment system
- Examination system
- Certificate generation
- Staff management
- Attendance and payroll
- And more...

**To update:** Edit the markdown file directly. Changes are loaded when the chatbot service initializes.

## API Endpoints

### POST `/api/chatbot/chat`

Send a message to the chatbot.

**Request:**
```json
{
  "message": "How do I register as a student?",
  "context": {
    "additional": "context"
  }
}
```

**Response:**
```json
{
  "response": "To register as a new student...",
  "source": "faq",
  "confidence": 0.95,
  "related_questions": [
    "What is my student ID format?",
    "What courses are available?"
  ],
  "faq_id": "reg_001"
}
```

### GET `/api/chatbot/suggestions`

Get quick suggestion buttons.

**Response:**
```json
[
  {
    "text": "How to register?",
    "query": "How do I register as a student?"
  },
  ...
]
```

### GET `/api/chatbot/health`

Check chatbot service health.

**Response:**
```json
{
  "status": "healthy",
  "gemini_enabled": true,
  "knowledge_base_loaded": true,
  "faq_count": 6
}
```

## Frontend Integration

The ChatWidget component (`rtsfrontend/components/chat/ChatWidget.tsx`) is already integrated:

- Floating chat button in bottom-right corner
- Real-time messaging
- Loading indicators
- Quick suggestions
- Related questions
- Error handling

## Testing

### Test FAQ System

```bash
# Test with common question
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "how to register"}'
```

### Test Gemini Fallback

```bash
# Test with complex question
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "What is the difference between ADCA and DCA courses?"}'
```

## Troubleshooting

### Chatbot not responding

1. Check backend is running: `http://localhost:8000/health`
2. Check chatbot health: `http://localhost:8000/api/chatbot/health`
3. Verify JWT token is valid
4. Check browser console for errors

### Gemini not working

1. Verify API key is set in `.env`
2. Check API key is valid at https://ai.google.dev/
3. Check chatbot health endpoint shows `gemini_enabled: true`
4. Review backend logs for errors

### FAQ not matching

1. Check question variations in `faq_config.py`
2. Add more variations for better matching
3. Lower threshold in `search_faq()` function (default: 0.3)

### Knowledge base not loading

1. Verify `knowledge_base.md` exists in `rtsbackend/`
2. Check file permissions
3. Review backend logs for file read errors

## Performance

- **FAQ responses**: < 100ms (instant)
- **Gemini responses**: 1-3 seconds (depends on API)
- **Concurrent users**: Supports multiple simultaneous chats
- **Cost**: FAQ is free, Gemini has usage limits (generous free tier)

## Cost Optimization

1. **FAQ First**: Most queries answered by FAQ (free)
2. **Gemini Fallback**: Only complex queries use Gemini
3. **Caching**: Consider caching common Gemini responses
4. **Rate Limiting**: Implement if needed for high traffic

## Future Enhancements

- [ ] Add conversation history/context
- [ ] Implement caching for Gemini responses
- [ ] Add analytics for common questions
- [ ] Support file attachments
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Integration with ticketing system

## Support

For issues or questions:
- Check this documentation
- Review backend logs
- Test with `/api/chatbot/health` endpoint
- Contact system administrator

---

**Last Updated:** December 2024
**Version:** 1.0.0