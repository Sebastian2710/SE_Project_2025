import os
import rpyc
from rpyc.utils.server import ThreadedServer
from recommender import algorithms
from recommender import data_loader

class RecommendationService(rpyc.Service):
    """
    RPyC Adapter for the Recommendation Engine.
    """

    def exposed_warmup(self) -> bool:
        algorithms._INTERACTION_MATRIX = None
        algorithms._ITEM_SIMILARITY = None
        return True

    def exposed_load_interactions(self, interactions_netref) -> bool:
        """
        Receives live data from Auction Service and injects it into the
        algorithm's memory.
        """
        # 1. Deserialize RPyC objects
        clean_data = []
        for item in interactions_netref:
            clean_data.append({
                "user_id": int(item["user_id"]),
                "item_id": int(item["item_id"]),
                "rating": float(item["rating"])
            })

        print(f"[Server] Received {len(clean_data)} interactions from Auction Service.")

        # 2. INJECTION: Create the closure that returns our live data
        def injected_loader():
            return clean_data
            
        # 3. SAVE ORIGINAL REFERENCES
        # We must save the function from BOTH locations to be safe
        original_loader_source = data_loader.load_interactions
        original_loader_dest = getattr(algorithms, "load_interactions", None)

        try:
            # 4. APPLY MONKEY PATCH
            # Patch the source module
            data_loader.load_interactions = injected_loader
            
            # CRITICAL FIX: Patch the destination module where it was imported!
            if hasattr(algorithms, "load_interactions"):
                algorithms.load_interactions = injected_loader
            
            # 5. FORCE REBUILD
            algorithms._INTERACTION_MATRIX = None
            algorithms._ITEM_SIMILARITY = None
            
            # This will now call our injected_loader()
            algorithms._ensure_models_loaded()
            print("[Server] Models rebuilt successfully with live data.")
            
        except Exception as e:
            print(f"[Server] Error processing interactions: {e}")
            return False
        finally:
            # 6. RESTORE ORIGINALS (Cleanup)
            data_loader.load_interactions = original_loader_source
            if original_loader_dest:
                algorithms.load_interactions = original_loader_dest

        return True

    def exposed_recommend_for_user(self, user_id: int, top_n: int = 10):
        return algorithms.get_recommendations_for_user(int(user_id), int(top_n))

    def exposed_similar_items(self, item_id: int, top_n: int = 10):
        return algorithms.get_similar_items(int(item_id), int(top_n))

# ---------- Server Bootstrap ----------

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
    print(f"[Recommender] RPyC server listening on {host}:{port}")
    server.start()

if __name__ == "__main__":
    host = os.getenv("RECOMMENDER_HOST", "127.0.0.1")
    port = int(os.getenv("RECOMMENDER_PORT", "18861"))
    run_server(host, port)