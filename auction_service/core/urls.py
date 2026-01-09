from django.urls import path

from .views import (
    hello,
    recommend_for_user,
    place_bid,
    decide_bid,
    home,
    seller_sell_item,
    seller_dashboard,
    buyer_auctions,
    buyer_auction_detail,
    buyer_dashboard,
    api_auctions,
    api_auction_state,
    api_seller_auctions,
)

urlpatterns = [
    # Landing
    path("", home, name="home"),
    path("hello/", hello, name="hello"),

    # Existing API
    path("recommend/<int:user_id>/", recommend_for_user, name="recommend_for_user"),
    path("bid/place/", place_bid, name="place_bid"),
    path("bid/<int:bid_id>/decision/", decide_bid, name="decide_bid"),

    # Seller UI
    path("seller/sell/", seller_sell_item, name="seller_sell_item"),
    path("seller/dashboard/", seller_dashboard, name="seller_dashboard"),

    # Buyer UI
    path("buyer/auctions/", buyer_auctions, name="buyer_auctions"),
    path("buyer/auction/<int:item_id>/", buyer_auction_detail, name="buyer_auction_detail"),
    path("buyer/<int:user_id>/", buyer_dashboard, name="buyer_dashboard"),


    # Polling JSON endpoints
    path("api/auctions/", api_auctions, name="api_auctions"),
    path("api/auction/<int:item_id>/state/", api_auction_state, name="api_auction_state"),
    path("api/seller/<int:seller_id>/auctions/", api_seller_auctions, name="api_seller_auctions"),
]
