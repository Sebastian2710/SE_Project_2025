# auction_service/core/services/recommender_client.py

from typing import Any, Dict, List, Optional

import rpyc
from django.conf import settings

from .protocol_checker import AuctionRecommenderMonitor


class RecommendationClient:
    """
    Robust RPyC client used by Django to talk to the Recommendation Service.

    - Lazy connection (connect on first use)
    - Reconnects automatically if the connection drops
    - Enforces Auction–Recommender MPST monitor per request/response cycle
    - Converts RPyC netref results into plain Python objects (no pickling)
    """

    def __init__(self) -> None:
        self._conn: Optional[rpyc.Connection] = None

    def _connect(self) -> rpyc.Connection:
        host: str = getattr(settings, "RECOMMENDER_HOST", "127.0.0.1")
        port: int = getattr(settings, "RECOMMENDER_PORT", 18861)
        timeout: int = getattr(settings, "RECOMMENDER_TIMEOUT_SECONDS", 3)

        return rpyc.connect(
            host,
            port,
            config={"sync_request_timeout": timeout},
        )

    def _get_connection(self) -> rpyc.Connection:
        if self._conn is None:
            self._conn = self._connect()
            return self._conn

        try:
            if self._conn.closed:
                self._conn = self._connect()
        except Exception:
            self._conn = self._connect()

        return self._conn

    def _call(self, fn_name: str, *args: Any) -> Any:
        """
        One retry on failure: if the server restarted, we reconnect once.
        """
        conn = self._get_connection()
        try:
            return getattr(conn.root, fn_name)(*args)
        except Exception:
            self._conn = None
            conn = self._get_connection()
            return getattr(conn.root, fn_name)(*args)

    def _materialize_list_of_dicts(self, value: Any) -> List[Dict[str, Any]]:
        """
        Convert an RPyC netref (list of dict-like objects) into plain Python types.
        This avoids using pickle (which we keep disabled for safety).
        Expected shape: [{"item_id": <int>, "score": <float>}, ...]
        """
        result: List[Dict[str, Any]] = []
        for row in value:
            # row may be a netref dict; extract primitives explicitly
            item_id = int(row["item_id"])
            score = float(row["score"])
            result.append({"item_id": item_id, "score": score})
        return result

    def warmup(self) -> bool:
        # warmup is not part of the MPST protocol; it's a lifecycle optimization.
        return bool(self._call("warmup"))

    def get_recommendations_for_user(self, user_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
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

    def get_similar_items(self, item_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
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


# Simple singleton instance for the app
recommender_client = RecommendationClient()
