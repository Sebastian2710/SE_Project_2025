from typing import List


class ProtocolViolation(Exception):
    """Raised when the protocol rules are violated."""
    pass


# ======================================================================
#  Generic Session Logger (you can keep this for debugging)
# ======================================================================
class SessionLog:
    """
    Very simple session logger/checker.
    We keep this as a utility, but the real protocol rules are enforced
    by the monitor classes derived from the Scribble projections.
    """

    def __init__(self) -> None:
        self.events: List[str] = []

    def record(self, event: str) -> None:
        self.events.append(event)

    def validate(self) -> None:
        # Placeholder – real checks implemented in the monitors
        return


# ======================================================================
#  Auction Bidding Monitor  (Buyer → Auction → Seller)
#  Derived from buyer_auction_seller_Auction.local
# ======================================================================
class AuctionBiddingMonitor:
    """
    Runtime checker for the Auction role in the Buyer–Auction–Seller protocol.

    States:
        START          – Waiting for Bid() from Buyer
        BID_RECEIVED   – Received Bid(), may send BidInfo()
        WAIT_DECISION  – Sent BidInfo(), waiting for Confirm() or Reject()
        CONFIRMED      – Got Confirm(), must send AcceptBid()
        REJECTED       – Got Reject(), must send RejectBid()
        DONE           – Final response sent
    """

    def __init__(self):
        self.state = "START"

    # --- Incoming events ------------------------------------------------

    def recv_bid_from_buyer(self):
        if self.state != "START":
            raise ProtocolViolation(
                f"Unexpected Bid() in state {self.state}"
            )
        self.state = "BID_RECEIVED"

    def recv_confirm_from_seller(self):
        if self.state != "WAIT_DECISION":
            raise ProtocolViolation(
                f"Unexpected Confirm() in state {self.state}"
            )
        self.state = "CONFIRMED"

    def recv_reject_from_seller(self):
        if self.state != "WAIT_DECISION":
            raise ProtocolViolation(
                f"Unexpected Reject() in state {self.state}"
            )
        self.state = "REJECTED"

    # --- Outgoing events ------------------------------------------------

    def send_bidinfo_to_seller(self):
        if self.state != "BID_RECEIVED":
            raise ProtocolViolation(
                f"Cannot send BidInfo() in state {self.state}"
            )
        self.state = "WAIT_DECISION"

    def send_acceptbid_to_buyer(self):
        if self.state != "CONFIRMED":
            raise ProtocolViolation(
                f"Cannot send AcceptBid() in state {self.state}"
            )
        self.state = "DONE"

    def send_rejectbid_to_buyer(self):
        if self.state != "REJECTED":
            raise ProtocolViolation(
                f"Cannot send RejectBid() in state {self.state}"
            )
        self.state = "DONE"


# ======================================================================
#  Auction–Recommender Monitor
#  Derived from auction_recommender_Auction.local
# ======================================================================
class AuctionRecommenderMonitor:
    """
    Runtime checker for the Auction role in the Auction–Recommender protocol.

    States:
        IDLE            – No outstanding request
        WAITING_RECS    – Sent GetRecs(), waiting for RecList() or RecError()
        WAITING_SIM     – Sent GetSimilar(), waiting for SimilarList() or RecError()
        DONE            – One complete request/response cycle finished
    """

    def __init__(self):
        self.state = "IDLE"

    # --- Outgoing events ------------------------------------------------

    def send_get_recs(self):
        if self.state != "IDLE":
            raise ProtocolViolation(
                f"Cannot send GetRecs() while in state {self.state}"
            )
        self.state = "WAITING_RECS"

    def send_get_similar(self):
        if self.state != "IDLE":
            raise ProtocolViolation(
                f"Cannot send GetSimilar() while in state {self.state}"
            )
        self.state = "WAITING_SIM"

    # --- Incoming events ------------------------------------------------

    def recv_rec_list(self):
        if self.state != "WAITING_RECS":
            raise ProtocolViolation(
                f"Unexpected RecList() in state {self.state}"
            )
        self.state = "DONE"

    def recv_similar_list(self):
        if self.state != "WAITING_SIM":
            raise ProtocolViolation(
                f"Unexpected SimilarList() in state {self.state}"
            )
        self.state = "DONE"

    def recv_rec_error(self):
        if self.state not in ("WAITING_RECS", "WAITING_SIM"):
            raise ProtocolViolation(
                f"Unexpected RecError() in state {self.state}"
            )
        self.state = "DONE"
