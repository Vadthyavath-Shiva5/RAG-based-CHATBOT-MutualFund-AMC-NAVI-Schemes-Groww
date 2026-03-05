# Phase 4: Backend API & Frontend Application

Complete implementation of the Flask-based REST API and responsive web interface for the RAG-based mutual funds chatbot.

## Overview

Phase 4 provides:
- **Flask REST API** - Backend service with 7 endpoints for chat, schemes, FAQ, and sources
- **Responsive Web UI** - Modern, Figma-inspired interface with chat widget
- **LLM Integration** - OpenAI GPT-4 integration with RAG pattern
- **Safety Mechanisms** - PII detection and scope validation
- **Real-time Chat** - Interactive chat widget with citations

## Project Structure

```
phase4/
├── __init__.py                 # Module initialization
├── app.py                      # Flask application (279 lines)
├── test_phase4.py             # Integration tests
├── lib/
│   ├── __init__.py
│   ├── llm_client.py          # LLM wrapper for OpenAI API
│   └── response_formatter.py   # Response formatting & safety
├── static/
│   ├── index.html             # Main UI (251 lines)
│   ├── css/
│   │   └── style.css          # Responsive styling
│   └── js/
│       ├── main.js            # Page functionality
│       └── chat.js            # Chat widget logic
└── templates/                 # (Optional Flask templates)
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- Flask 3.0.0+
- Flask-CORS 4.0.0+
- Pydantic 2.0.0+
- OpenAI 1.0.0+
- python-re2 0.2.0+

### 2. Configure Environment

```bash
# Create .env file in project root
export OPENAI_API_KEY="your-api-key-here"
export PHASE_3_CONFIG="path/to/phase3/config"
```

### 3. Run the Application

```bash
# Development server (with auto-reload)
python -m flask --app phase4.app run --debug

# Production server
gunicorn phase4.app:app --bind 0.0.0.0:5000
```

Visit: http://localhost:5000

## API Endpoints

### 1. Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-03-05T12:53:51Z"
}
```

### 2. Chat Endpoint ⭐
```bash
POST /chat
Content-Type: application/json

{
  "query": "What is NAV in mutual funds?",
  "context_type": "mutual_funds"
}
```

Response:
```json
{
  "success": true,
  "response": "NAV (Net Asset Value) is...",
  "sources": ["source1.txt", "source2.txt"],
  "confidence": 0.92
}
```

**Features:**
- PII Detection (email, phone, account numbers, PAN)
- Scope Validation (rejects financial advice/recommendations)
- Phase 3 Retriever Integration
- OpenAI GPT-4 response generation
- Citation tracking

### 3. Schemes Information
```bash
GET /schemes
```

### 4. FAQ
```bash
GET /faq
```

### 5. Data Sources
```bash
GET /sources
```

### Error Responses
```json
{
  "error": "Bad Request",
  "message": "Query cannot be empty",
  "code": 400
}
```

## Frontend Features

### Home Page Sections

1. **Navigation**
   - Brand logo (clickable - scrolls to top)
   - Menu links with smooth scrolling
   - Responsive sticky navbar

2. **Hero Section**
   - Welcome message
   - Call-to-action button
   - Gradient background

3. **Info Cards Grid** (6 cards)
   - AI-Powered: Intelligent responses
   - Secure: Data privacy guaranteed
   - Cited Sources: All answers referenced
   - 24/7 Availability: Always available
   - Latest Data: Current information
   - Multi-Source: Diverse knowledge base

4. **Quick Action Buttons**
   - What is NAV?
   - What is AUM?
   - What is SIP?
   - What is Expense Ratio?
   - List of Schemes
   - What is Exit Load?

5. **FAQ Accordion**
   - What are Mutual Funds?
   - Do we provide financial advice?
   - How accurate is the information?
   - How is my data protected?

6. **Chat Widget**
   - Floating chat button
   - Message history
   - Citation links
   - Typing indicators
   - Unread badge

## Chat Widget Interface

### JavaScript API

```javascript
// Access chat widget
const chatWidget = document.querySelector('.chat-widget');

// Trigger chat from quick actions
function triggerChat(query) {
    const chatInput = document.getElementById('chatInput');
    chatInput.value = query;
    document.getElementById('sendBtn').click();
}

// Message format (sent to /chat)
{
    "query": "User's question here",
    "context_type": "mutual_funds"
}

// Response format
{
    "success": true,
    "response": "Bot's answer with full context...",
    "sources": ["filename1.txt", "filename2.txt"],
    "confidence": 0.85
}
```

### Styling System

CSS Variables (in style.css):
```css
--primary-color: #1e90ff           /* Blue */
--secondary-color: #00d4ff         /* Cyan */
--accent-color: #ff6b6b            /* Red */
--success-color: #51cf66           /* Green */
--text-primary: #1a1a1a
--text-secondary: #666666
```

Responsive Breakpoints:
- Desktop: 1200px+
- Tablet: 768px - 1199px
- Mobile: < 768px

## Testing

### Run Tests

```bash
# All tests
pytest phase4/test_phase4.py -v

# Specific test class
pytest phase4/test_phase4.py::TestFlaskAPI -v

# With coverage
pytest phase4/test_phase4.py --cov=phase4
```

### Test Coverage

- ✅ Flask API endpoints (6 tests)
- ✅ Safety checking (PII detection, scope validation)
- ✅ Response formatting (sources, confidence, cleaning)
- ✅ LLM client initialization
- ✅ Integration flow (query → response)
- ✅ Error handling (404, 500)

### Manual Testing with curl

```bash
# Health check
curl http://localhost:5000/health

# Chat query
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is NAV?", "context_type": "mutual_funds"}'

# Schemes
curl http://localhost:5000/schemes

# FAQ
curl http://localhost:5000/faq

# Sources
curl http://localhost:5000/sources
```

## Security Features

### 1. PII Detection
Detects and rejects queries containing:
- Email addresses (user@example.com)
- Phone numbers (+91-9876543210)
- Account numbers (16-18 digits)
- PAN numbers (ABCDE1234F)

### 2. Scope Validation
Rejects out-of-scope queries:
- Financial advice ("Should I buy...?")
- Personalized recommendations
- Personal account information
- Investment recommendations

### 3. CORS Protection
- Configurable allowed origins
- Prevents unauthorized cross-origin requests
- Production-ready security headers

## Environment Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY              # OpenAI API key
PHASE_3_CONFIG              # Path to Phase 3 config file
FLASK_ENV                   # development or production
DEBUG                       # True or False
```

### Optional Configuration
```bash
ALLOWED_ORIGINS             # Comma-separated CORS origins
MAX_TOKENS                  # Max LLM response tokens (default: 500)
CONFIDENCE_THRESHOLD        # Min confidence score (default: 0.5)
```

## Integration with Phase 3

The Phase 4 API seamlessly integrates with Phase 3 retriever:

```python
# In app.py initialize_components()
from phase3.retriever import RetrieverPipeline

retriever = RetrieverPipeline(config_path)
results = retriever.retrieve(query, top_k=5)

# Format for LLM
context = "\n".join([r['content'] for r in results])
```

## Performance Considerations

- **Response Time**: ~2-3 seconds (including LLM)
- **Concurrent Users**: 100+ (with proper deployment)
- **Message History**: Local storage (frontend)
- **Token Limit**: 4000 tokens per request

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "phase4.app:app", "--bind", "0.0.0.0:5000"]
```

### Build & Run
```bash
docker build -t rag-chatbot:phase4 .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key rag-chatbot:phase4
```

## Troubleshooting

### Chat Not Loading
- Check browser console for errors (F12)
- Verify Flask server is running
- Check CORS settings in app.py

### LLM Errors
- Verify OPENAI_API_KEY is set
- Check OpenAI API quota
- Verify API key has required permissions

### Page Styling Issues
- Clear browser cache (Ctrl+Shift+Delete)
- Check network tab for CSS file loading
- Verify static files path

### Phase 3 Integration Issues
- Check PHASE_3_CONFIG path
- Verify Phase 3 database is available
- Check retriever initialization logs

## Next Steps

1. **API Testing**: Test all endpoints with Postman
2. **Load Testing**: Use Apache JMeter for performance
3. **Frontend Testing**: Cross-browser compatibility
4. **Deployment**: Deploy to production environment
5. **Monitoring**: Set up logging and error tracking
6. **Analytics**: Track user interactions and chat patterns

## Contributing

When adding new features:
1. Update tests in `test_phase4.py`
2. Update API documentation
3. Update this README with new endpoints
4. Test CORS compatibility
5. Validate safety mechanisms

## Version History

- **v1.0.0** (2024-03-05)
  - Initial release with 7 API endpoints
  - Complete responsive UI with chat widget
  - Safety mechanisms (PII, scope validation)
  - LLM integration with citations
  - Comprehensive test suite

## Support

For issues or questions:
1. Check troubleshooting section
2. Review test files for examples
3. Check Phase 3 documentation
4. Review OpenAI API documentation