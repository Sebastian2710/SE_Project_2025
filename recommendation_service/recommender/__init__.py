"""
Recommender package.

This package contains:
- interaction data loading utilities
- collaborative filtering algorithms for recommending items
- item similarity computation

The main user-facing functions are:
    get_recommendations_for_user(user_id, top_n)
    get_similar_items(item_id, top_n)
"""

from .algorithms import get_recommendations_for_user, get_similar_items
from .data_loader import load_interactions

__all__ = [
    "get_recommendations_for_user",
    "get_similar_items",
    "load_interactions",
]
