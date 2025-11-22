"""
Exa API Client Wrapper
Neural search engine integration with highlights and content extraction
"""
import os
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """Search result data structure"""
    title: str
    url: str
    text: str
    score: float
    highlights: List[str]
    published_date: Optional[str] = None
    author: Optional[str] = None
    
    def __repr__(self):
        return f"SearchResult(title='{self.title[:50]}...', url='{self.url}', score={self.score:.3f})"


class ExaClient:
    """
    Wrapper for Exa API
    Provides neural search with automatic content extraction
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Exa client
        
        Args:
            api_key: Exa API key (defaults to EXA_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('EXA_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "EXA_API_KEY not found. "
                "Set it as environment variable or pass to constructor."
            )
        
        # Import Exa SDK
        try:
            from exa_py import Exa
            self.client = Exa(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "exa_py package not installed. "
                "Install with: pip install exa-py"
            )
    
    def search(
        self,
        query: str,
        num_results: int = 5,
        include_highlights: bool = True,
        use_autoprompt: bool = True,
        category: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search the web using Exa's neural search
        
        Args:
            query: Search query
            num_results: Number of results to return (max 10 for free tier)
            include_highlights: Include highlighted snippets
            use_autoprompt: Use Exa's autoprompt for better results
            category: Filter by category (e.g., 'news', 'research paper')
        
        Returns:
            List of SearchResult objects
        """
        try:
            # Perform search with content
            search_response = self.client.search_and_contents(
                query=query,
                num_results=min(num_results, 10),
                use_autoprompt=use_autoprompt,
                text=True,
                highlights=include_highlights if include_highlights else None,
                category=category,
            )
            
            # Parse results
            results = []
            for result in search_response.results:
                # Extract highlights
                highlights = []
                if include_highlights and hasattr(result, 'highlights') and result.highlights:
                    highlights = result.highlights
                
                # Get text content
                text = ""
                if hasattr(result, 'text') and result.text:
                    text = result.text
                
                # Create SearchResult object
                search_result = SearchResult(
                    title=result.title or "Untitled",
                    url=result.url,
                    text=text,
                    score=result.score if hasattr(result, 'score') else 0.0,
                    highlights=highlights,
                    published_date=result.published_date if hasattr(result, 'published_date') else None,
                    author=result.author if hasattr(result, 'author') else None
                )
                
                results.append(search_result)
            
            return results
            
        except Exception as e:
            # Fallback: return error as search result
            print(f"Exa search error: {e}")
            return [
                SearchResult(
                    title="Search Error",
                    url="",
                    text=f"Error performing search: {str(e)}",
                    score=0.0,
                    highlights=[]
                )
            ]
    
    def find_similar(
        self,
        url: str,
        num_results: int = 5,
        include_highlights: bool = True,
    ) -> List[SearchResult]:
        """
        Find similar content to a given URL
        
        Args:
            url: URL to find similar content for
            num_results: Number of results
            include_highlights: Include highlights
        
        Returns:
            List of SearchResult objects
        """
        try:
            response = self.client.find_similar_and_contents(
                url=url,
                num_results=min(num_results, 10),
                text=True,
                highlights=include_highlights if include_highlights else None,
            )
            
            results = []
            for result in response.results:
                highlights = []
                if include_highlights and hasattr(result, 'highlights') and result.highlights:
                    highlights = result.highlights
                
                text = result.text if hasattr(result, 'text') and result.text else ""
                
                results.append(SearchResult(
                    title=result.title or "Untitled",
                    url=result.url,
                    text=text,
                    score=result.score if hasattr(result, 'score') else 0.0,
                    highlights=highlights,
                ))
            
            return results
            
        except Exception as e:
            print(f"Exa find_similar error: {e}")
            return []


# Singleton instance
_exa_client = None


def get_exa_client(api_key: Optional[str] = None) -> ExaClient:
    """
    Get or create Exa client singleton
    
    Args:
        api_key: Optional API key (uses env var if not provided)
    
    Returns:
        ExaClient instance
    """
    global _exa_client
    
    if _exa_client is None:
        _exa_client = ExaClient(api_key=api_key)
    
    return _exa_client


# Example usage and testing
if __name__ == "__main__":
    print("Testing Exa API Client...")
    
    try:
        client = get_exa_client()
        
        # Test search
        print("\n" + "="*70)
        print("TEST: Searching for 'AI agents'")
        print("="*70)
        
        results = client.search("AI agents", num_results=3)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Score: {result.score:.3f}")
            print(f"   Text: {result.text[:150]}...")
            if result.highlights:
                print(f"   Highlights: {result.highlights[:2]}")
        
        print("\n" + "="*70)
        print("✅ Exa client test successful!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure EXA_API_KEY is set in your environment:")
        print("  export EXA_API_KEY='your-api-key'")
