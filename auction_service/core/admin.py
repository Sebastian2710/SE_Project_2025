from django.contrib import admin

from .models import Buyer, Seller, Item, Bid

admin.site.register(Buyer)
admin.site.register(Seller)
admin.site.register(Item)
admin.site.register(Bid)
