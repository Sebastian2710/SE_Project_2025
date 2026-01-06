from typing import List, Dict, Any
import numpy as np # type: ignore
import pandas as pd # type: ignore
from sklearn.metrics.pairwise import cosine_similarity # type: ignore

from .data_loader import load_interactions


# Cached data structures (lazy-loaded)
_INTERACTION_MATRIX = None
_ITEM_IDS = None
_USER_IDS = None
_ITEM_SIMILARITY = None


def _ensure_models_loaded():
    """
    Lazily loads and builds the item similarity model.
    This prevents recomputation on every request.
    """
    global _INTERACTION_MATRIX, _ITEM_IDS, _USER_IDS, _ITEM_SIMILARITY

    if _INTERACTION_MATRIX is not None:
        return  # already loaded

    interactions = load_interactions()

    if not interactions:
        # fallback mock data so service still works
        data = pd.DataFrame(
            {
                "user_id": [1, 1, 2, 2, 3],
                "item_id": [101, 102, 101, 103, 104],
                "rating": [5, 3, 4, 2, 5],
            }
        )
    else:
        data = pd.DataFrame(interactions)

    # Pivot into user–item matrix
    matrix = data.pivot_table(
        index="user_id",
        columns="item_id",
        values="rating",
        fill_value=0,
    )

    _INTERACTION_MATRIX = matrix
    _USER_IDS = matrix.index.to_list()
    _ITEM_IDS = matrix.columns.to_list()

    # Compute cosine similarity between all item vectors
    item_vectors = matrix.T  # shape: items × users
    sim = cosine_similarity(item_vectors)

    _ITEM_SIMILARITY = pd.DataFrame(sim, index=_ITEM_IDS, columns=_ITEM_IDS)


def get_recommendations_for_user(user_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Item-based collaborative filtering recommendation.
    Looks at items the user interacted with and finds similar items.
    """
    _ensure_models_loaded()

    if user_id not in _USER_IDS:
        return []  # unknown user

    user_vector = _INTERACTION_MATRIX.loc[user_id]
    interacted_items = user_vector[user_vector > 0].index.tolist()

    if not interacted_items:
        return []  # cold start user

    # Aggregate similarity scores across all items the user liked
    scores = np.zeros(len(_ITEM_IDS))

    for item in interacted_items:
        scores += _ITEM_SIMILARITY.loc[item].values * user_vector[item]

    # Remove items the user already interacted with
    for item in interacted_items:
        idx = _ITEM_IDS.index(item)
        scores[idx] = -np.inf

    # Get top items
    top_indices = np.argsort(scores)[::-1][:top_n]

    recommendations = [
        {"item_id": _ITEM_IDS[i], "score": float(scores[i])}
        for i in top_indices
        if scores[i] != -np.inf
    ]

    return recommendations


def get_similar_items(item_id: int, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Returns items with highest cosine similarity to the given item.
    """
    _ensure_models_loaded()

    if item_id not in _ITEM_IDS:
        return []

    sims = _ITEM_SIMILARITY.loc[item_id].drop(item_id)  # remove itself
    top = sims.sort_values(ascending=False).head(top_n)

    return [
        {"item_id": int(idx), "score": float(score)}
        for idx, score in top.items()
    ]
