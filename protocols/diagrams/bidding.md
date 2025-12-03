# Bidding Protocol – Sequence Diagram (Buyer ↔ Auction ↔ Seller)

## Mermaid Diagram

```mermaid
sequenceDiagram
    participant B as Buyer
    participant A as Auction
    participant S as Seller

    B->>A: Bid()
    A->>S: AskSeller()

    alt Seller confirms
        S->>A: Confirm()
        A->>B: AcceptBid()
    else Seller rejects
        S->>A: Reject()
        A->>B: RejectBid()
    end
```

## ASCII Diagram (optional)

```
            +----------------+
            |     Buyer     |
            +----------------+
                     |
                     |  Bid()
                     v
            +----------------+
            |    Auction     |
            +----------------+
                     |
                     |  AskSeller()
                     v
            +----------------+
            |     Seller     |
            +----------------+
                 /       \
                /         \
        Confirm()       Reject()
              \           /
               \         /
                v       v
            +----------------+
            |    Auction     |
            +----------------+
                 /       \
                /         \
      AcceptBid()     RejectBid()
                \       /
                 \     /
                  v   v
            +----------------+
            |     Buyer      |
            +----------------+
```
