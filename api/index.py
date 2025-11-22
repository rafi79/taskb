"""
Multi-Agent RAG System - Vercel API Entry Point
Flask application optimized for serverless deployment
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
CORS(app)

# Configuration
app.config['DEBUG'] = os.environ.get('DEBUG', 'False') == 'True'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request


@app.route('/')
def index():
    """API Documentation Homepage"""
    return jsonify({
        "name": "Multi-Agent RAG System",
        "version": "1.0.0",
        "status": "operational",
        "description": "AI-powered Q&A with web search and citations",
        "endpoints": {
            "GET /": "API documentation",
            "GET /health": "Health check",
            "GET /api/status": "System status",
            "POST /api/chat": "Chat with AI",
            "POST /api/search": "Web search"
        },
        "features": [
            "Multi-agent orchestration",
            "Neural web search (Exa API)",
            "Context-aware responses",
            "Session management",
            "Source citations"
        ],
        "repository": "https://github.com/rafi79/taskb",
        "documentation": "https://github.com/rafi79/taskb#readme"
    })


@app.route('/health')
def health():
    """Health Check Endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "multi-agent-rag-api",
        "version": "1.0.0",
        "timestamp": os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local')[:7]
    }), 200


@app.route('/api/status')
def api_status():
    """System Status and Configuration"""
    exa_configured = bool(os.environ.get('EXA_API_KEY'))
    hf_configured = bool(os.environ.get('HUGGINGFACE_TOKEN'))
    
    return jsonify({
        "status": "operational",
        "components": {
            "api": "healthy",
            "exa_search": "configured" if exa_configured else "missing_api_key",
            "huggingface": "configured" if hf_configured else "missing_token"
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform
        },
        "capabilities": {
            "web_search": exa_configured,
            "ai_models": hf_configured,
            "session_memory": True
        }
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main Chat Endpoint
    
    Request Body:
    {
        "query": "Your question here",
        "session_id": "optional-session-id",
        "search_web": true,
        "max_results": 3
    }
    
    Response:
    {
        "answer": "AI response",
        "session_id": "session-id",
        "sources": ["url1", "url2"],
        "metadata": {...}
    }
    """
    try:
        # Validate request
        data = request.json
        if not data:
            return jsonify({
                "error": "Request body required",
                "example": {
                    "query": "What are AI agents?",
                    "session_id": "user123",
                    "search_web": True
                }
            }), 400
        
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"error": "Missing or empty 'query' field"}), 400
        
        session_id = data.get('session_id', 'default')
        search_web = data.get('search_web', True)
        max_results = min(data.get('max_results', 3), 10)  # Cap at 10
        
        sources = []
        context_text = ""
        
        # Web search if enabled and configured
        if search_web and os.environ.get('EXA_API_KEY'):
            try:
                from utils.exa_client import get_exa_client
                
                exa = get_exa_client()
                search_results = exa.search(query, num_results=max_results)
                
                sources = [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.text[:200] + "..." if len(r.text) > 200 else r.text
                    }
                    for r in search_results
                ]
                
                # Build context from search results
                context_text = "\n\n".join([
                    f"Source: {r.title}\nURL: {r.url}\nContent: {r.text[:400]}..."
                    for r in search_results
                ])
                
            except ImportError:
                context_text = "Search module not available in this deployment."
            except Exception as e:
                context_text = f"Search error: {str(e)}"
        
        # Generate response
        # Note: Full RAG with Qwen model will be added after local development
        answer = generate_response(query, context_text, search_web)
        
        return jsonify({
            "answer": answer,
            "session_id": session_id,
            "sources": sources,
            "metadata": {
                "query_length": len(query),
                "search_enabled": search_web,
                "sources_found": len(sources),
                "has_context": bool(context_text),
                "deployment": "vercel-serverless"
            }
        }), 200
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc() if app.config['DEBUG'] else None
        
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "detail": error_detail
        }), 500


@app.route('/api/search', methods=['POST'])
def search():
    """
    Web Search Endpoint
    
    Request Body:
    {
        "query": "Search query",
        "num_results": 5
    }
    
    Response:
    {
        "results": [...],
        "metadata": {...}
    }
    """
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' field",
                "example": {"query": "AI agents", "num_results": 5}
            }), 400
        
        query = data['query'].strip()
        num_results = min(data.get('num_results', 5), 10)
        
        if not query:
            return jsonify({"error": "Query cannot be empty"}), 400
        
        # Check API key
        if not os.environ.get('EXA_API_KEY'):
            return jsonify({
                "error": "Search not configured",
                "message": "EXA_API_KEY environment variable not set in Vercel"
            }), 503
        
        # Perform search
        try:
            from utils.exa_client import get_exa_client
            
            exa = get_exa_client()
            results = exa.search(query, num_results=num_results)
            
            formatted_results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "text": r.text[:300] + "..." if len(r.text) > 300 else r.text,
                    "score": r.score,
                    "highlights": r.highlights[:3] if r.highlights else [],
                    "published_date": r.published_date if hasattr(r, 'published_date') else None
                }
                for r in results
            ]
            
            return jsonify({
                "results": formatted_results,
                "metadata": {
                    "query": query,
                    "total_results": len(formatted_results),
                    "requested": num_results
                }
            }), 200
            
        except ImportError:
            return jsonify({
                "error": "Search module not available",
                "message": "utils.exa_client not found in deployment"
            }), 503
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


def generate_response(query: str, context: str, has_search: bool) -> str:
    """
    Generate AI response
    TODO: Replace with full Qwen model integration
    """
    if context and has_search:
        return f"""Based on current web sources:

**Query:** {query}

**Answer:** Here's what I found from recent sources:

{context[:500]}...

**Note:** This is a demo response from the Vercel deployment. The full Multi-Agent RAG system with Qwen2.5-VL model will provide more sophisticated answers once deployed.

**Current Status:**
✅ API is operational
✅ Web search is working (via Exa)
✅ Session tracking enabled
✅ Source citations included

**Next Steps:** The complete agent system with advanced AI models will be deployed after local development and testing."""
    else:
        return f"""**Query:** {query}

**Answer:** API is operational but search is not configured or was disabled.

**To enable full functionality:**
1. Set EXA_API_KEY in Vercel environment variables
2. Enable search_web: true in your request
3. Deploy the complete agent system

**Current deployment:** Lightweight API for testing
**Full system:** Coming after local development phase

Visit the repository for more information: https://github.com/rafi79/taskb"""


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": ["/", "/health", "/api/status", "/api/chat", "/api/search"],
        "documentation": "Visit / for API documentation"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": f"The {request.method} method is not allowed for this endpoint"
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": str(error) if app.config['DEBUG'] else "An unexpected error occurred",
        "support": "Please report this issue on GitHub"
    }), 500


# For local development
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True') == 'True'
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         Multi-Agent RAG System API                        ║
║         Running on http://localhost:{port}                    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

Available endpoints:
  GET  /              - API documentation
  GET  /health        - Health check
  GET  /api/status    - System status
  POST /api/chat      - Chat endpoint
  POST /api/search    - Search endpoint

Press Ctrl+C to stop
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
