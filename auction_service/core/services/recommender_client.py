from typing import Any, Dict, List, Optional
import logging
import rpyc
from django.conf import settings

from core.models import Bid
from .protocol_checker import AuctionRecommenderMonitor

logger = logging.getLogger(__name__)

class RecommendationClient:
    """
    Robust RPyC client used by Django to talk to the Recommendation Service.
    """

    def __init__(self) -> None:
        self._conn: Optional[rpyc.Connection] = None

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    def _connect(self) -> rpyc.Connection:
        host: str = getattr(settings, "RECOMMENDER_HOST", "127.0.0.1")
        port: int = getattr(settings, "RECOMMENDER_PORT", 18861)
        # Increased timeout slightly to allow for data transfer
        timeout: int = getattr(settings, "RECOMMENDER_TIMEOUT_SECONDS", 5)

        return rpyc.connect(
            host,
            port,
            config={
                "sync_request_timeout": timeout,
                "allow_pickle": False,
            },
        )

    def _get_connection(self) -> rpyc.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
        return self._conn

    def _call(self, fn_name: str, *args: Any) -> Any:
        try:
            return getattr(self._get_connection().root, fn_name)(*args)
        except Exception:
            # Simple retry logic
            self._conn = None
            return getattr(self._get_connection().root, fn_name)(*args)

    # ------------------------------------------------------------------
    # Interaction loader (DB -> plain Python)
    # ------------------------------------------------------------------

    def build_interactions_from_db(self) -> List[Dict[str, Any]]:
        interactions: List[Dict[str, Any]] = []
        # Optimization: Filter out bids with no amount
        qs = Bid.objects.select_related("buyer", "item").filter(amount__isnull=False)

        for bid in qs:
            interactions.append({
                "user_id": bid.buyer_id,
                "item_id": bid.item_id,
                "rating": float(bid.amount),
            })
        return interactions

    def push_interactions_to_recommender(self) -> None:
        """Send all interactions to the Recommendation Service."""
        interactions = self.build_interactions_from_db()
        # Only push if we actually have data
        if interactions:
            self._call("load_interactions", interactions)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _materialize_list_of_dicts(self, value: Any) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        # Handle cases where RPyC returns None or empty
        if not value:
            return []
            
        for row in value:
            result.append({
                "item_id": int(row["item_id"]),
                "score": float(row["score"]),
            })
        return result

    # ------------------------------------------------------------------
    # Public API used by Django views
    # ------------------------------------------------------------------

    def warmup(self) -> bool:
        return bool(self._call("warmup"))

    def get_recommendations_for_user(
        self, user_id: int, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        
        # ### CRITICAL FIX START ###
        # We MUST push the data before asking for recommendations,
        # otherwise the separate service has no idea who this user is.
        try:
            self.push_interactions_to_recommender()
        except Exception as e:
            logger.warning(f"Failed to sync data to recommender: {e}")
        # ### CRITICAL FIX END ###

        monitor = AuctionRecommenderMonitor()
        monitor.send_get_recs()

        try:
            raw = self._call("recommend_for_user", int(user_id), int(top_n))
            result = self._materialize_list_of_dicts(raw)
            monitor.recv_rec_list()
            return result
        except Exception:
            monitor.recv_rec_error()
            raise

    def get_similar_items(
        self, item_id: int, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        
        # Note: We don't necessarily need to push data for 'similar items' 
        # if the matrix is already built, but it's safer to keep it consistent.
        
        monitor = AuctionRecommenderMonitor()
        monitor.send_get_similar()

        try:
            raw = self._call("similar_items", int(item_id), int(top_n))
            result = self._materialize_list_of_dicts(raw)
            monitor.recv_similar_list()
            return result
        except Exception:
            monitor.recv_rec_error()
            raise

# Singleton instance
recommender_client = RecommendationClient()