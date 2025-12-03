# SafeBid Protocol Specification  
**Multiparty Session Types (MPST) – Global & Local Protocols**

This document describes the communication protocols used in the SafeBid system using **Multiparty Session Types**.  
MPST ensures that all participating components (Buyer, Auction Service, Seller, Recommendation Service) follow a **correct, deadlock-free, and consistent message order**.

The protocol specifications are written in **Scribble**, and the corresponding local types are generated using the Scribble toolchain.

---

## 1. Overview of Roles

SafeBid consists of four communicating roles:

- **Buyer** – submits bids for items.
- **Auction Service** – central coordinator; receives bids, contacts the seller, decides the final outcome, and requests recommendations.
- **Seller** – confirms or rejects bids forwarded by the auction service.
- **Recommendation Service** – provides personalized or item-based recommendations to the auction service.

Two separate multiparty protocols describe these interactions:

1. **Bidding Protocol** (Buyer ↔ Auction ↔ Seller)  
2. **Recommendation Protocol** (Auction ↔ Recommendation Service)

---

## 2. Global Protocols (Scribble)

The formal MPST global specifications are located in:

/protocols/buyer_auction_seller.scr
/protocols/auction_recommender.scr


These `.scr` files define the **legal message order** between all participants.

### 2.1 Bidding Protocol (Buyer–Auction–Seller)

This protocol enforces:

- A bid must be **processed fully by the auction** before notifying the buyer.
- The auction may **optionally consult the seller** via `AskSeller`.
- The seller may respond with **Confirm** or **Reject**.
- The auction must send **exactly one final outcome** to the buyer:
  - `AcceptBid` (only after seller Confirm), or  
  - `RejectBid`  
- No direct Buyer ↔ Seller messages are permitted.

Example (simplified):

Buyer → Auction: Bid()
Auction → Seller: AskSeller()
Seller → Auction: Confirm | Reject
Auction → Buyer: AcceptBid | RejectBid


### 2.2 Recommendation Protocol (Auction–RecService)

This protocol enforces:

- The Auction initiates either:
  - `GetRecommendations()`  
  - or `GetSimilarItems()`
- The Recommendation Service must respond with **exactly one**:
  - a result list, or  
  - a `RecError()`  
- No additional messages are allowed in that cycle.

Example (simplified):

Auction → RecService: GetRecommendations | GetSimilarItems
RecService → Auction: (List | RecError)


---

## 3. Local Protocol Projections

Scribble automatically generates a **local view** (endpoint protocol) for each participating role.

These projections are stored under:

/docs/projections/

Files include:

- `buyer_local.scr`
- `seller_local.scr`
- `auction_local.scr`
- `recommender_local.scr`
- `auction_recommender_local.scr`

Each file describes **only the actions** allowed by that specific role, e.g.:

- order of send/receive actions  
- allowed branches  
- exactly one final decision  
- no illegal message interleavings  

These projections are what the implementers (Auction, Buyer, etc.) must follow in the Python/RPyC code.

---

## 4. Runtime Protocol Monitors

Although Scribble enforces correctness at the specification level, we also implemented **runtime monitors** for the Auction role in Python:

protocol_checker.py


The main classes are:

- `AuctionBiddingMonitor`  
- `AuctionRecommenderMonitor`  

These monitors enforce:

### 4.1 Bidding Monitor Rules
- The auction must receive `Bid()` first.
- It may send `BidInfo()` only after receiving a bid.
- After contacting the seller, it must wait for:
  - `Confirm()` → then must send `AcceptBid()`
  - `Reject()` → then must send `RejectBid()`
- After sending the final outcome, the protocol ends (`DONE` state).

### 4.2 Recommendation Monitor Rules
- Auction may only send a request in the `IDLE` state.
- After sending a request:
  - Only **one** response is allowed (`RecList`, `SimilarList`, or `RecError`).
- No other messages are allowed until the request cycle finishes.

### 4.3 ProtocolViolation
Violations are reported via:

```python
raise ProtocolViolation("Description")
