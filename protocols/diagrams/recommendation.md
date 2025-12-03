# Recommendation Protocol – Sequence Diagram (Auction ↔ RecService)

## Mermaid Diagram

```mermaid
sequenceDiagram
    participant A as Auction
    participant R as RecService

    alt GetRecommendations
        A->>R: GetRecommendations()
        alt Success
            R->>A: RecommendationsList()
        else Error
            R->>A: RecError()
        end
    else GetSimilarItems
        A->>R: GetSimilarItems()
        alt Success
            R->>A: SimilarItemsList()
        else Error
            R->>A: RecError()
        end
    end
```

## ASCII Diagram (optional)

```
            +----------------+
            |    Auction     |
            +----------------+
               /         \
              /           \
   GetRecommendations()   GetSimilarItems()
            |                   |
            v                   v
     +---------------+    +---------------+
     | Rec Service   |    | Rec Service   |
     +---------------+    +---------------+
          /     \               /      \
         /       \             /        \
   RecList()   RecError()  SimilarList()  RecError()
```
