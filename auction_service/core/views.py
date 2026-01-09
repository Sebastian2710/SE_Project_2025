import json
from typing import Any, Dict

from django.http import JsonResponse, HttpRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import Buyer, Item, Bid
from .services.protocol_checker import AuctionBiddingMonitor, ProtocolViolation
from .services.recommender_client import recommender_client

from datetime import timedelta
from django.shortcuts import redirect
from django.utils import timezone
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from .models import Buyer, Bid, Item


from .models import Seller  # add Seller import
_BIDDING_MONITORS: Dict[str, AuctionBiddingMonitor] = {}


def _get_monitor(session_id: str, strict: bool = False) -> AuctionBiddingMonitor:
    """
    Each bidding protocol run is single-use (ends in DONE).
    For the UI demo, we want repeated bids to work by default, so we reset
    the monitor automatically once it reaches DONE.

    If strict=True, we do NOT reset on DONE (useful to demonstrate violations).
    """
    monitor = _BIDDING_MONITORS.get(session_id)
    if monitor is None:
        monitor = AuctionBiddingMonitor()
        _BIDDING_MONITORS[session_id] = monitor
        return monitor

    if (not strict) and getattr(monitor, "state", None) == "DONE":
        monitor = AuctionBiddingMonitor()
        _BIDDING_MONITORS[session_id] = monitor

    return monitor



def hello(request):
    return render(request, "core/hello.html")

# --- ADD these helper functions somewhere near the top (after hello is fine) ---
def _refresh_item_status(item: Item) -> bool:
    """
    Recompute status from timing:
    - before start_time -> COMING_SOON
    - between start_time and end_time -> LIVE
    - after end_time -> ENDED

    Returns True if status changed (and was saved).
    """
    now = timezone.now()
    end_time = item.start_time + timedelta(seconds=int(item.duration_seconds))

    if now < item.start_time:
        new_status = Item.Status.COMING_SOON
    elif now >= end_time:
        new_status = Item.Status.ENDED
    else:
        new_status = Item.Status.LIVE

    if item.status != new_status:
        item.status = new_status
        item.save(update_fields=["status"])
        return True
    return False


def _refresh_items_status(items) -> None:
    # If seller ended it early (direct sale), NEVER override it via timing rules.
    for it in items:
        if it.status == Item.Status.ENDED:
            return False
        _refresh_item_status(it)


def _item_time_remaining_seconds(item: Item) -> int:
    """
    For UI clarity:
    - COMING_SOON: seconds until START
    - LIVE: seconds until END
    - ENDED: 0
    """
    now = timezone.now()
    end_time = item.start_time + timedelta(seconds=int(item.duration_seconds))

    if item.status == Item.Status.COMING_SOON:
        remaining = int((item.start_time - now).total_seconds())
        return max(0, remaining)

    if item.status == Item.Status.LIVE:
        remaining = int((end_time - now).total_seconds())
        return max(0, remaining)

    return 0



# --- ADD UI page views ---
def home(request: HttpRequest):
    return render(request, "core/home.html")


def seller_sell_item(request: HttpRequest):
    sellers = Seller.objects.order_by("username")

    if request.method == "GET":
        return render(request, "core/seller_sell.html", {"sellers": sellers})

    # POST (simple form submit, no JSON)
    seller_id = request.POST.get("seller_id")
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    starting_price = request.POST.get("starting_price")
    start_time = request.POST.get("start_time")  # datetime-local string
    duration_seconds = request.POST.get("duration_seconds")

    if not seller_id or not name or not starting_price or not start_time or not duration_seconds:
        return render(
            request,
            "core/seller_sell.html",
            {"sellers": sellers, "error": "Missing required fields."},
            status=400,
        )

    try:
        seller = Seller.objects.get(id=int(seller_id))
        sp = float(starting_price)
        ds = int(duration_seconds)

        # Parse datetime-local (YYYY-MM-DDTHH:MM)
        # Django can parse with fromisoformat; make it aware in current tz if naive.
        dt = timezone.datetime.fromisoformat(start_time)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

    except Seller.DoesNotExist:
        return render(request, "core/seller_sell.html", {"sellers": sellers, "error": "Seller not found."}, status=404)
    except Exception:
        return render(request, "core/seller_sell.html", {"sellers": sellers, "error": "Invalid input types."}, status=400)

    item = Item.objects.create(
        name=name,
        description=description,
        seller=seller,
        starting_price=sp,
        current_price=sp,
        start_time=dt,
        duration_seconds=ds,
        status=Item.Status.COMING_SOON,  # will refresh automatically
    )

    return redirect(f"/seller/dashboard/?seller_id={seller.id}&created_item_id={item.id}")


def seller_dashboard(request: HttpRequest):
    sellers = Seller.objects.order_by("username")
    seller_id = request.GET.get("seller_id")

    selected_seller = None
    if seller_id:
        try:
            selected_seller = Seller.objects.get(id=int(seller_id))
        except Exception:
            selected_seller = None

    return render(
        request,
        "core/seller_dashboard.html",
        {
            "sellers": sellers,
            "selected_seller": selected_seller,
            "created_item_id": request.GET.get("created_item_id"),
        },
    )


def buyer_auctions(request: HttpRequest):
    buyers = Buyer.objects.order_by("username")
    return render(request, "core/buyer_auctions.html", {"buyers": buyers})


def buyer_auction_detail(request: HttpRequest, item_id: int):
    buyers = Buyer.objects.order_by("username")
    try:
        item = Item.objects.select_related("seller", "highest_bidder").get(id=item_id)
        _refresh_item_status(item)
    except Item.DoesNotExist:
        return render(request, "core/buyer_auction_detail.html", {"buyers": buyers, "error": "Auction not found."}, status=404)

    return render(
        request,
        "core/buyer_auction_detail.html",
        {"buyers": buyers, "item_id": item.id},
    )

# --- ADD JSON polling endpoints ---
def api_auctions(request: HttpRequest):
    status_filter = request.GET.get("status")  # LIVE / COMING_SOON / ENDED or None

    qs = Item.objects.select_related("seller", "highest_bidder").all().order_by("-id")
    items = list(qs)

    _refresh_items_status(items)

    if status_filter:
        items = [it for it in items if it.status == status_filter]

    data = []
    for it in items:
        data.append(
            {
                "id": it.id,
                "name": it.name,
                "seller": it.seller.username,
                "status": it.status,
                "current_price": float(it.current_price),
                "starting_price": float(it.starting_price),
                "highest_bidder": it.highest_bidder.username if it.highest_bidder else None,
                "time_remaining_seconds": _item_time_remaining_seconds(it),
            }
        )

    return JsonResponse({"auctions": data})


def api_auction_state(request: HttpRequest, item_id: int):
    try:
        item = Item.objects.select_related("seller", "highest_bidder").get(id=item_id)
        _refresh_item_status(item)
    except Item.DoesNotExist:
        return JsonResponse({"error": "Auction not found"}, status=404)

    bids = (
        Bid.objects.select_related("buyer")
        .filter(item=item)
        .order_by("-timestamp")[:10]
    )

    return JsonResponse(
        {
            "item": {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "seller": item.seller.username,
                "status": item.status,
                "current_price": float(item.current_price),
                "starting_price": float(item.starting_price),
                "highest_bidder": item.highest_bidder.username if item.highest_bidder else None,
                "time_remaining_seconds": _item_time_remaining_seconds(item),
            },
            "recent_bids": [
                {
                    "id": b.id,
                    "buyer": b.buyer.username,
                    "amount": float(b.amount),
                    "status": b.status,
                    "timestamp": b.timestamp.isoformat(),
                }
                for b in bids
            ],
        }
    )


def api_seller_auctions(request: HttpRequest, seller_id: int):
    try:
        seller = Seller.objects.get(id=seller_id)
    except Seller.DoesNotExist:
        return JsonResponse({"error": "Seller not found"}, status=404)

    items = list(
        Item.objects.select_related("highest_bidder")
        .filter(seller=seller)
        .order_by("-id")
    )
    _refresh_items_status(items)

    # Include pending bids so seller can confirm/reject from dashboard
    item_ids = [it.id for it in items]
    pending_bids = (
        Bid.objects.select_related("buyer", "item")
        .filter(item_id__in=item_ids, status=Bid.Status.PENDING)
        .order_by("-timestamp")
    )

    pending_by_item: Dict[int, list] = {}
    for b in pending_bids:
        pending_by_item.setdefault(b.item_id, []).append(
            {
                "id": b.id,
                "buyer": b.buyer.username,
                "amount": float(b.amount),
                "timestamp": b.timestamp.isoformat(),
            }
        )

    data = []
    for it in items:
        data.append(
            {
                "id": it.id,
                "name": it.name,
                "status": it.status,
                "current_price": float(it.current_price),
                "highest_bidder": it.highest_bidder.username if it.highest_bidder else None,
                "time_remaining_seconds": _item_time_remaining_seconds(it),
                "pending_bids": pending_by_item.get(it.id, []),
            }
        )

    return JsonResponse({"seller": seller.username, "auctions": data})

def recommend_for_user(request, user_id: int):
    top_n = int(request.GET.get("top_n", "10"))
    recommendations = recommender_client.get_recommendations_for_user(user_id=user_id, top_n=top_n)
    return JsonResponse({"user_id": user_id, "top_n": top_n, "recommendations": recommendations})


def _is_auto_accept_live_bid(item: Item, buyer: Buyer, amount: float) -> bool:
    if item.status != Item.Status.LIVE:
        return False

    if amount <= float(item.current_price):
        return False

    if item.highest_bidder is not None and item.highest_bidder.id == buyer.id:
        return False

    return True


@csrf_exempt
def place_bid(request: HttpRequest):
    """
    POST JSON:
    {
      "session_id": "demo1",
      "buyer_id": 1,
      "item_id": 1,
      "amount": 250
    }

    Behavior:
    - COMING_SOON: creates PENDING bid, waits for seller decision via /bid/decision/
    - LIVE: auto-accepts if higher than current_price and bidder is not current highest bidder
    """
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)

    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    session_id = str(payload.get("session_id", "default"))
    buyer_id = payload.get("buyer_id")
    item_id = payload.get("item_id")
    amount = payload.get("amount")

    if buyer_id is None or item_id is None or amount is None:
        return JsonResponse({"error": "Missing required fields: buyer_id, item_id, amount"}, status=400)

    try:
        buyer = Buyer.objects.get(id=int(buyer_id))
        item = Item.objects.select_related("seller", "highest_bidder").get(id=int(item_id))
        bid_amount = float(amount)
    except Buyer.DoesNotExist:
        return JsonResponse({"error": "Buyer not found", "session_id": session_id}, status=404)
    except Item.DoesNotExist:
        return JsonResponse({"error": "Item not found", "session_id": session_id}, status=404)
    except Exception:
        return JsonResponse({"error": "Invalid types for buyer_id/item_id/amount"}, status=400)

    strict = str(request.GET.get("strict", "0")) == "1"
    monitor = _get_monitor(session_id, strict=strict)


    try:
        # Buyer -> Auction: Bid()
        monitor.recv_bid_from_buyer() #comment to show protocol violation

        # Record bid (status depends on auction state)
        if item.status == Item.Status.COMING_SOON:
            bid = Bid.objects.create(buyer=buyer, item=item, amount=bid_amount, status=Bid.Status.PENDING)

            # Auction -> Seller: BidInfo()
            monitor.send_bidinfo_to_seller()

            return JsonResponse(
                {
                    "session_id": session_id,
                    "status": "PENDING_SELLER_DECISION",
                    "bid_id": bid.id,
                    "buyer_id": buyer.id,
                    "seller_id": item.seller.id,
                    "item_id": item.id,
                    "amount": bid.amount,
                }
            )

        if item.status == Item.Status.LIVE:
            bid = Bid.objects.create(buyer=buyer, item=item, amount=bid_amount, status=Bid.Status.PENDING)

            # Auction -> Seller: BidInfo() (Option B: conceptual notify)
            monitor.send_bidinfo_to_seller()

            if _is_auto_accept_live_bid(item, buyer, bid_amount):
                # Seller -> Auction: Confirm() (auto-confirm)
                monitor.recv_confirm_from_seller()

                bid.status = Bid.Status.ACCEPTED
                bid.save()

                item.current_price = bid_amount
                item.highest_bidder = buyer
                item.save()

                # Auction -> Buyer: AcceptBid()
                monitor.send_acceptbid_to_buyer()

                return JsonResponse(
                    {
                        "session_id": session_id,
                        "status": "ACCEPTED",
                        "bid_id": bid.id,
                        "buyer_id": buyer.id,
                        "seller_id": item.seller.id,
                        "item_id": item.id,
                        "amount": bid.amount,
                        "current_price": item.current_price,
                        "highest_bidder_id": buyer.id,
                    }
                )

            # Auto-reject if not valid
            monitor.recv_reject_from_seller()  # auto-reject (Option B)
            bid.status = Bid.Status.REJECTED
            bid.save()

            monitor.send_rejectbid_to_buyer()

            return JsonResponse(
                {
                    "session_id": session_id,
                    "status": "REJECTED",
                    "reason": "Bid must be higher than current price and bidder must not already be highest bidder.",
                    "bid_id": bid.id,
                    "buyer_id": buyer.id,
                    "seller_id": item.seller.id,
                    "item_id": item.id,
                    "amount": bid.amount,
                    "current_price": item.current_price,
                    "highest_bidder_id": item.highest_bidder.id if item.highest_bidder else None,
                }
            )

        if item.status == Item.Status.ENDED:
            return JsonResponse({"error": "Auction ended", "session_id": session_id, "item_id": item.id}, status=400)

        return JsonResponse({"error": "Invalid item status", "session_id": session_id}, status=400)

    except ProtocolViolation as ex:
        return JsonResponse(
            {"error": "Protocol violation", "details": str(ex), "session_id": session_id},
            status=409,
        )


@csrf_exempt
def decide_bid(request: HttpRequest, bid_id: int):
    """
    Seller decision endpoint for COMING_SOON bids.

    POST JSON:
    {
      "session_id": "demo1",
      "decision": "confirm" | "reject"
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)

    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    session_id = str(payload.get("session_id", "default"))
    decision = str(payload.get("decision", "")).lower()

    if decision not in ("confirm", "reject"):
        return JsonResponse({"error": "decision must be 'confirm' or 'reject'"}, status=400)

    strict = str(request.GET.get("strict", "0")) == "1"
    monitor = _get_monitor(session_id, strict=strict)


    try:
        bid = Bid.objects.select_related("buyer", "item", "item__seller").get(id=int(bid_id))
    except Bid.DoesNotExist:
        return JsonResponse({"error": "Bid not found", "bid_id": bid_id, "session_id": session_id}, status=404)

    item = bid.item

    if item.status != Item.Status.COMING_SOON:
        return JsonResponse({"error": "Seller decision allowed only for COMING_SOON items"}, status=400)

    if bid.status != Bid.Status.PENDING:
        return JsonResponse({"error": "Bid is not pending", "bid_status": bid.status}, status=400)

    try:
        if decision == "confirm":
            monitor.recv_confirm_from_seller()

            with transaction.atomic():
                # Reload inside transaction to avoid race conditions
                bid = Bid.objects.select_related("buyer", "item").select_for_update().get(id=bid.id)
                item = Item.objects.select_for_update().get(id=item.id)

                bid.status = Bid.Status.ACCEPTED
                bid.save(update_fields=["status"])

                # Update winner + price (direct sale)
                if bid.amount > float(item.current_price):
                    item.current_price = float(bid.amount)
                item.highest_bidder = bid.buyer

                # IMPORTANT: end listing immediately (direct sale)
                item.status = Item.Status.ENDED
                item.save(update_fields=["current_price", "highest_bidder", "status"])

                # Reject all other pending bids for this item
                Bid.objects.filter(item=item, status=Bid.Status.PENDING).exclude(id=bid.id).update(status=Bid.Status.REJECTED)

            monitor.send_acceptbid_to_buyer()

            return JsonResponse(
                {
                    "session_id": session_id,
                    "status": "ACCEPTED_AND_ENDED",
                    "bid_id": bid.id,
                    "item_id": item.id,
                    "amount": bid.amount,
                    "current_price": item.current_price,
                    "highest_bidder_id": item.highest_bidder.id if item.highest_bidder else None,
                    "item_status": item.status,
                }
            )


        monitor.recv_reject_from_seller()
        bid.status = Bid.Status.REJECTED
        bid.save()

        monitor.send_rejectbid_to_buyer()

        return JsonResponse(
            {"session_id": session_id, "status": "REJECTED", "bid_id": bid.id, "item_id": item.id}
        )

    except ProtocolViolation as ex:
        return JsonResponse(
            {"error": "Protocol violation", "details": str(ex), "session_id": session_id},
            status=409,
        )

def buyer_dashboard(request: HttpRequest, user_id: int):
    """
    Buyer Dashboard (demo mode)
    - URL: /buyer/<user_id>/
    - Shows auctions this buyer has bid on
    - Fetches recommendations from the separate service
    """
    # Get buyer or 404
    buyer = get_object_or_404(Buyer, id=user_id)

    # Auctions this buyer has bid on
    items = (
        Item.objects.select_related("seller", "highest_bidder")
        .filter(bid__buyer=buyer)
        .distinct()
        .order_by("-id")
    )

    # Recommendations from Raisa's service
    try:
        recommendations = recommender_client.get_recommendations_for_user(user_id=buyer.id, top_n=5)
        print("Recommender output for buyer", buyer.id, ":", recommendations)

        recommended_items = Item.objects.filter(id__in=[r["item_id"] for r in recommendations])
    except Exception:
        recommended_items = []

    # Render template
    return render(
        request,
        "core/buyer_dashboard.html",
        {
            "buyer": buyer,
            "items": items,
            "recommended_items": recommended_items,
            "user_id": buyer.id,  # for JS calls
        },
    )
