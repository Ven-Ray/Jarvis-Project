"""
Search Manager - Central orchestration for all web searches.
Coordinates classification, provider selection, execution, and result normalization.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import SearchRequest, SearchResult
from .classifier import SearchClassifier
from .providers.base import SearchProvider


logger = logging.getLogger("jarvis.web_search")


class SearchManager:
    """Central manager for all web search operations."""
    
    def __init__(self, providers: List[SearchProvider], classifier=None):
        self.providers = providers
        self.classifier = classifier or SearchClassifier()
    
    async def execute(self, request_id: str, original_query: str, 
                      location: Optional[Dict] = None) -> SearchResult:
        """Execute a complete search workflow.
        
        Args:
            request_id: Unique identifier for this request
            original_query: User's original query text
            location: Optional location data dict
            
        Returns:
            Normalized SearchResult object
        """
        logger.info(f"[{request_id}] REQUEST_STARTED - {original_query}")
        
        # Step 1: Classify intent
        classification = self.classifier.classify(original_query)
        logger.info(f"[{request_id}] REQUEST_CLASSIFIED - requires_web_search={classification['requires_web_search']}")
        
        if not classification["requires_web_search"]:
            return SearchResult(
                request_id=request_id,
                original_query=original_query,
                data=None,
                error="No web search required"
            )
        
        # Step 2: Create search request object
        search_request = SearchRequest(
            request_id=request_id,
            original_query=original_query,
            interpreted_query=classification["search_query"],
            location=location
        )
        logger.info(f"[{request_id}] ENTITIES_EXTRACTED - query={search_request.interpreted_query}")
        
        # Step 3: Select provider
        provider = self._select_provider(search_request)
        provider_name = type(provider).__name__
        logger.info(f"[{request_id}] PROVIDER_SELECTED - {provider_name}")
        
        # Step 4: Execute search with timeout (run in thread to handle blocking I/O)
        logger.info(f"[{request_id}] SEARCH_STARTED")
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(provider.search, search_request),
                timeout=30.0
            )
            logger.info(f"[{request_id}] SEARCH_COMPLETED - success={result.is_valid()}")
        except asyncio.TimeoutError:
            logger.warning(f"[{request_id}] SEARCH_TIMEOUT")
            result = SearchResult(
                request_id=request_id,
                original_query=original_query,
                error="Search timed out after 30 seconds"
            )
        
        # Step 5: Validate and normalize results
        if result.is_valid():
            logger.info(f"[{request_id}] RESULTS_NORMALIZED")
            logger.info(f"[{request_id}] FRESHNESS_VALIDATED - age={result.freshness}s")
            
            if result.conflicts:
                logger.warning(f"[{request_id}] CONFLICTS_DETECTED - {len(result.conflicts)} conflicts")
        
        # Step 6: Generate response or use fallback
        if not result.is_valid():
            logger.info(f"[{request_id}] FALLBACK_RESPONSE_USED")
            result = self._generate_fallback_result(search_request)
        
        logger.info(f"[{request_id}] REQUEST_COMPLETED")
        return result
    
    def _select_provider(self, request: SearchRequest) -> SearchProvider:
        """Select the most appropriate provider for this request."""
        # Try specialized providers first
        for provider in self.providers:
            if isinstance(provider, type(self.providers[-1])):
                continue  # Skip general fallback
            
            try:
                if provider.supports(request):
                    return provider
            except Exception as e:
                logger.warning(f"Provider {type(provider).__name__} supports() failed: {e}")
        
        # Fall back to general search provider (last in list)
        return self.providers[-1]
    
    def _generate_fallback_result(self, request: SearchRequest) -> SearchResult:
        """Generate a deterministic fallback response from normalized data."""
        query = request.interpreted_query or request.original_query
        
        # Try to provide useful information even without successful search
        if "weather" in query.lower():
            return SearchResult(
                request_id=request.request_id,
                category="weather",
                original_query=request.original_query,
                data=f"I'm sorry, Sir. I was unable to retrieve current weather information at this time."
            )
        
        return SearchResult(
            request_id=request.request_id,
            original_query=request.original_query,
            interpreted_query=query,
            data=f"I'm sorry, Sir. I was unable to find reliable information about: {query}"
        )
