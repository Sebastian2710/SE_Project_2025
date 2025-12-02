import rpyc


class RecommendationClient:
    """
    Thin RPyC client used by the Django views to talk
    to the Recommendation Service.
    """

    def __init__(self, host: str = "localhost", port: int = 18861) -> None:
        self.host = host
        self.port = port
        self._conn = None

    def _get_connection(self):
        if self._conn is None:
            self._conn = rpyc.connect(self.host, self.port)
        return self._conn

    def get_recommendations_for_user(self, user_id: int, top_n: int = 10):
        conn = self._get_connection()
        return conn.root.get_recommendations_for_user(user_id, top_n)

    def get_similar_items(self, item_id: int, top_n: int = 10):
        conn = self._get_connection()
        return conn.root.get_similar_items(item_id, top_n)
