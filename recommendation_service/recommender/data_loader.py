"""
Utilities for loading interactions (views, bids, purchases)
from CSV / database / mock data.
"""

from typing import List, Dict, Any
from pathlib import Path
import pandas as pd # type: ignore


# Default path where interaction data can live
DATA_DIR = Path(__file__).parent / "data"
INTERACTIONS_CSV = DATA_DIR / "interactions.csv"


def load_interactions() -> List[Dict[str, Any]]:
    """
    Loads user–item interactions used by the recommender.

    Expected schema (implicit or explicit feedback):
        user_id   : int
        item_id   : int
        rating    : float   (or derived score)

    Priority:
    1. CSV file (if exists)
    2. Mock fallback data
    """

    if INTERACTIONS_CSV.exists():
        return _load_from_csv(INTERACTIONS_CSV)

    # Fallback so recommender always works
    return _load_mock_data()


def _load_from_csv(path: Path) -> List[Dict[str, Any]]:
    """
    Load interactions from a CSV file.
    """
    try:
        df = pd.read_csv(path)

        required_cols = {"user_id", "item_id", "rating"}
        if not required_cols.issubset(df.columns):
            raise ValueError(
                f"CSV must contain columns {required_cols}, "
                f"found {set(df.columns)}"
            )

        # Ensure correct types
        df["user_id"] = df["user_id"].astype(int)
        df["item_id"] = df["item_id"].astype(int)
        df["rating"] = df["rating"].astype(float)

        return df.to_dict(orient="records")

    except Exception as e:
        print(f"[Recommender] Failed loading CSV data: {e}")
        print("[Recommender] Falling back to mock data.")
        return _load_mock_data()


def _load_mock_data() -> List[Dict[str, Any]]:
    """
    Small synthetic dataset for local testing and demos.
    """
    return [
        {"user_id": 1, "item_id": 101, "rating": 5.0},
        {"user_id": 1, "item_id": 102, "rating": 3.0},
        {"user_id": 2, "item_id": 101, "rating": 4.0},
        {"user_id": 2, "item_id": 103, "rating": 2.0},
        {"user_id": 3, "item_id": 104, "rating": 5.0},
        {"user_id": 3, "item_id": 101, "rating": 1.0},
    ]
