import rpyc
from rpyc.utils.server import ThreadedServer

from recommender.algorithms import (
    get_recommendations_for_user,
    get_similar_items,
)


class RecommendationService(rpyc.Service):
    """
    RPyC service exposing the recommender functions.
    Methods must be exposed_* to be callable remotely.
    """

    def exposed_get_recommendations_for_user(self, user_id: int, top_n: int = 10):
        return get_recommendations_for_user(user_id, top_n)

    def exposed_get_similar_items(self, item_id: int, top_n: int = 10):
        return get_similar_items(item_id, top_n)


def run_server(host: str = "localhost", port: int = 18861) -> None:
    server = ThreadedServer(RecommendationService, hostname=host, port=port)
    print(f"RPyC RecommendationService listening on {host}:{port}")
    server.start()


if __name__ == "__main__":
    run_server()
