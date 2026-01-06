from django.db import models
from django.utils import timezone


class Buyer(models.Model):
    username = models.CharField(max_length=50, unique=True)

    def __str__(self) -> str:
        return f"Buyer({self.username})"


class Seller(models.Model):
    username = models.CharField(max_length=50, unique=True)

    def __str__(self) -> str:
        return f"Seller({self.username})"


class Item(models.Model):
    class Status(models.TextChoices):
        COMING_SOON = "COMING_SOON", "Coming soon"
        LIVE = "LIVE", "Live"
        ENDED = "ENDED", "Ended"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)

    # Auction timing (seller sets these)
    start_time = models.DateTimeField(default=timezone.now)
    duration_seconds = models.PositiveIntegerField(default=3600)  # 1 hour

    # Auction state (for UI + rules)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMING_SOON)

    # Pricing
    starting_price = models.FloatField()
    current_price = models.FloatField(default=0.0)

    # Winner tracking (updated when bids are accepted)
    highest_bidder = models.ForeignKey(Buyer, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return f"Item({self.name})"


class Bid(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    # For COMING_SOON: bids start pending until seller (or auto-logic) decides
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self) -> str:
        return f"Bid(buyer={self.buyer}, item={self.item}, amount={self.amount}, status={self.status})"
