from typing import List, Dict, Any


def get_recommendations_for_user(user_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Placeholder implementation.

    Returns a list of item dicts:
    [{ "item_id": 1, "score": 0.95 }, ...]
    """
    # TODO (Raisa): replace with real collaborative filtering
    return [
        {"item_id": 101, "score": 0.9},
        {"item_id": 102, "score": 0.8},
    ][:top_n]


def get_similar_items(item_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Placeholder implementation.

    Returns items that are "similar" to the given item.
    """
    # TODO (Raisa): replace with real similarity logic
    return [
        {"item_id": item_id + 1, "score": 0.88},
        {"item_id": item_id + 2, "score": 0.75},
    ][:top_n]
