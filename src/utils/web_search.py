"""
Web Search Integration for Auto-GIT

Provides free, no-API-key search capabilities using:
- DuckDuckGo (web search, no limits)
- arXiv (research papers, academic)
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import arxiv
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class ArxivSearcher:
    """Search arXiv for research papers"""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search arXiv for papers
        
        Args:
            query: Search query (e.g., "transformer attention mechanism")
            max_results: Override default max results
            
        Returns:
            List of paper dictionaries with title, summary, authors, pdf_url, etc.
        """
        max_results = max_results or self.max_results
        
        try:
            logger.info(f"Starting arXiv search for: {query}")
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            papers = []
            for result in search.results():
                paper = {
                    "title": result.title,
                    "summary": result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
                    "authors": [author.name for author in result.authors],
                    "pdf_url": result.pdf_url,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "entry_id": result.entry_id
                }
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers for query: {query}")
            return papers
            
        except Exception as e:
            logger.error(f"arXiv search failed for '{query}': {e}")
            logger.debug(f"Error details: {type(e).__name__}: {str(e)}")
            return []


class DuckDuckGoSearcher:
    """Search web using DuckDuckGo (no API key required!)"""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search web with DuckDuckGo
        
        Args:
            query: Search query
            max_results: Override default max results
            
        Returns:
            List of result dictionaries with title, href, body
        """
        max_results = max_results or self.max_results
        
        try:
            logger.info(f"Starting DuckDuckGo search for: {query}")
            with DDGS(timeout=30) as ddgs:  # Increased timeout from default
                results = list(ddgs.text(query, max_results=max_results))
            
            logger.info(f"Found {len(results)} web results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for '{query}': {e}")
            logger.debug(f"Error details: {type(e).__name__}: {str(e)}")
            return []
    
    def search_news(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """Search recent news articles"""
        max_results = max_results or self.max_results
        
        try:
            with DDGS(timeout=20) as ddgs:
                results = list(ddgs.news(query, max_results=max_results))
            
            logger.info(f"Found {len(results)} news results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo news search failed: {e}")
            return []


class ResearchSearcher:
    """
    Combined research search using multiple sources
    
    Provides comprehensive search across academic and web sources
    """
    
    def __init__(self, max_arxiv: int = 5, max_web: int = 5):
        self.arxiv_searcher = ArxivSearcher(max_results=max_arxiv)
        self.web_searcher = DuckDuckGoSearcher(max_results=max_web)
    
    def search_comprehensive(self, topic: str) -> Dict[str, List[Dict]]:
        """
        Search both arXiv and web for a research topic
        
        Args:
            topic: Research topic or query
            
        Returns:
            Dictionary with 'papers', 'web_results', 'implementations' keys
        """
        results = {
            "papers": [],
            "web_results": [],
            "implementations": []
        }
        
        # Search arXiv for academic papers
        logger.info(f"Searching arXiv for: {topic}")
        results["papers"] = self.arxiv_searcher.search(topic)
        
        # Search web for general information
        logger.info(f"Searching web for: {topic}")
        results["web_results"] = self.web_searcher.search(topic)
        
        # Search for code implementations on GitHub
        implementation_query = f"{topic} implementation github"
        logger.info(f"Searching for implementations: {implementation_query}")
        results["implementations"] = self.web_searcher.search(implementation_query)
        
        return results
    
    def format_papers_for_prompt(self, papers: List[Dict]) -> str:
        """Format arXiv papers for LLM prompt context"""
        if not papers:
            return "No papers found."
        
        formatted = "## Related Research Papers\n\n"
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper["authors"][:3])
            if len(paper["authors"]) > 3:
                authors += " et al."
            
            formatted += f"{i}. **{paper['title']}**\n"
            formatted += f"   - Authors: {authors}\n"
            formatted += f"   - Published: {paper['published']}\n"
            formatted += f"   - Summary: {paper['summary']}\n"
            formatted += f"   - PDF: {paper['pdf_url']}\n\n"
        
        return formatted
    
    def format_web_results_for_prompt(self, results: List[Dict]) -> str:
        """Format web results for LLM prompt context"""
        if not results:
            return "No web results found."
        
        formatted = "## Web Search Results\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result.get('title', 'No title')}**\n"
            formatted += f"   - URL: {result.get('href', 'N/A')}\n"
            formatted += f"   - Snippet: {result.get('body', 'No description')[:200]}...\n\n"
        
        return formatted


# Convenience functions
def search_papers(query: str, max_results: int = 5) -> List[Dict]:
    """Quick arXiv paper search"""
    searcher = ArxivSearcher(max_results=max_results)
    return searcher.search(query)


def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """Quick web search"""
    searcher = DuckDuckGoSearcher(max_results=max_results)
    return searcher.search(query)


def search_all(topic: str, max_arxiv: int = 5, max_web: int = 5) -> Dict[str, List[Dict]]:
    """Quick comprehensive search"""
    searcher = ResearchSearcher(max_arxiv=max_arxiv, max_web=max_web)
    return searcher.search_comprehensive(topic)


if __name__ == "__main__":
    # Test searches
    logging.basicConfig(level=logging.INFO)
    
    print("Testing arXiv search...")
    papers = search_papers("efficient transformer attention", max_results=2)
    print(f"Found {len(papers)} papers")
    if papers:
        print(f"First paper: {papers[0]['title']}")
    
    print("\nTesting web search...")
    web_results = search_web("transformer attention mechanism", max_results=2)
    print(f"Found {len(web_results)} web results")
    if web_results:
        print(f"First result: {web_results[0].get('title', 'No title')}")
    
    print("\nTesting comprehensive search...")
    all_results = search_all("efficient transformers", max_arxiv=2, max_web=2)
    print(f"Papers: {len(all_results['papers'])}")
    print(f"Web results: {len(all_results['web_results'])}")
    print(f"Implementations: {len(all_results['implementations'])}")
