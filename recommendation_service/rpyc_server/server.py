import os
import rpyc
from rpyc.utils.server import ThreadedServer
from recommender import algorithms
from recommender import data_loader

class RecommendationService(rpyc.Service):
    """
    RPyC Adapter for the Recommendation Engine.
    
    This service bridges the gap between the external Auction Service
    and the internal Recommendation algorithms.
    """

    def exposed_warmup(self) -> bool:
        """Resets the internal model state."""
        # Manually reset globals since specific reset() might not exist in original
        algorithms._INTERACTION_MATRIX = None
        algorithms._ITEM_SIMILARITY = None
        return True

    def exposed_load_interactions(self, interactions_netref) -> bool:
        """
        Receives live data from Auction Service and injects it into the
        algorithm's memory.
        
        Args:
            interactions_netref: List of dicts sent via RPyC
        """
        # 1. Deserialize RPyC objects into a standard Python list
        #    This prevents "Netref" errors inside Pandas
        clean_data = []
        for item in interactions_netref:
            clean_data.append({
                "user_id": int(item["user_id"]),
                "item_id": int(item["item_id"]),
                "rating": float(item["rating"])
            })

        print(f"[Server] Received {len(clean_data)} interactions from Auction Service.")

        # 2. INJECTION: We temporarily override the data loader's source
        #    This tricks Raisa's code into loading our variable instead of the CSV.
        original_loader = data_loader.load_interactions
        
        def injected_loader():
            return clean_data
            
        try:
            # Apply the monkey patch
            data_loader.load_interactions = injected_loader
            
            # 3. Force the algorithm to reload
            #    We set the cache to None so _ensure_models_loaded() triggers a rebuild
            algorithms._INTERACTION_MATRIX = None
            algorithms._ITEM_SIMILARITY = None
            
            # Trigger the rebuild immediately using the injected data
            algorithms._ensure_models_loaded()
            print("[Server] Models rebuilt successfully with live data.")
            
        except Exception as e:
            print(f"[Server] Error processing interactions: {e}")
            return False
        finally:
            # Restore the original loader (Good citizenship)
            data_loader.load_interactions = original_loader

        return True

    def exposed_recommend_for_user(self, user_id: int, top_n: int = 10):
        # Ensure ID is an int (RPyC sometimes passes objects)
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