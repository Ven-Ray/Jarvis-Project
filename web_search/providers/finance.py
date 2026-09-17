"""Finance search provider for stocks, crypto, currency."""

from ..providers.base import SearchProvider


class FinanceProvider(SearchProvider):
    """Stocks, cryptocurrency, and market data provider."""
    
    def supports(self, request) -> bool:
        query_lower = (request.original_query or "").lower()
        return any(word in query_lower for word in [
            "stock", "stocks", "share", "shares", "crypto", "cryptocurrency",
            "bitcoin", "ethereum", "price of", "market", "nasdaq", "s&p",
            "dow jones", "forex", "currency"
        ])
    
    async def search(self, request):
        from ..models import SearchResult
        # TODO: Implement finance-specific search logic
        return SearchResult(
            request_id=request.request_id,
            category="finance",
            original_query=request.original_query,
            data=f"Finance search for: {request.original_query}"
        )
