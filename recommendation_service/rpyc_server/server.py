import os

import rpyc
from rpyc.utils.server import ThreadedServer

from recommender.algorithms import get_recommendations_for_user, get_similar_items
from recommender import algorithms as algorithms_module


class RecommendationService(rpyc.Service):
    """
    RPyC service exposing the recommender functions.

    Expose a stable RPC surface:
      - warmup()
      - recommend_for_user(user_id, top_n)
      - similar_items(item_id, top_n)

    Keep legacy method names too (get_*) for compatibility.
    """

    # ---- lifecycle ----
    def exposed_warmup(self) -> bool:
        algorithms_module._ensure_models_loaded()
        return True

    # ---- clean API ----
    def exposed_recommend_for_user(self, user_id: int, top_n: int = 10):
        return get_recommendations_for_user(int(user_id), int(top_n))

    def exposed_similar_items(self, item_id: int, top_n: int = 10):
        return get_similar_items(int(item_id), int(top_n))

    # ---- legacy API (do not remove yet) ----
    def exposed_get_recommendations_for_user(self, user_id: int, top_n: int = 10):
        return self.exposed_recommend_for_user(user_id, top_n)

    def exposed_get_similar_items(self, item_id: int, top_n: int = 10):
        return self.exposed_similar_items(item_id, top_n)


def run_server(host: str = "127.0.0.1", port: int = 18861) -> None:
    server = ThreadedServer(
        RecommendationService,
        hostname=host,
        port=port,
        protocol_config={
            "allow_public_attrs": False,
            "allow_all_attrs": False,
            "allow_pickle": False,
        },
    )
    print(f"RPyC RecommendationService listening on {host}:{port}")
    server.start()


if __name__ == "__main__":
    host = os.getenv("RECOMMENDER_HOST", "127.0.0.1")
    port = int(os.getenv("RECOMMENDER_PORT", "18861"))
    run_server(host, port)
