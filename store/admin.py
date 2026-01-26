from django.contrib import admin
from django.db.models import Sum, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.contrib.auth.models import Group

# IMPORT UNFOLD ADMIN
from unfold.admin import ModelAdmin, TabularInline

from .models import Product, Category, RestockBatch, Customer, Sale, SaleItem, Staff

admin.site.unregister(Group)


@admin.register(Product)
class ProductAdmin(ModelAdmin):  # Using Unfold's ModelAdmin
    list_display = (
        "name",
        "size",
        "color",
        "show_stock",
        "current_buy_price",
        "current_sell_price",
        "show_profit",
    )
    list_editable = ("current_sell_price",)
    search_fields = ("name", "color", "size")
    list_filter = ("category", "size")
    actions = ["quick_restock_5"]

    # Optimized Query for fast loading
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        bought_sub = (
            RestockBatch.objects.filter(product=OuterRef("pk"))
            .values("product")
            .annotate(total=Sum("quantity_added"))
            .values("total")
        )
        sold_sub = (
            SaleItem.objects.filter(product=OuterRef("pk"))
            .values("product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        return qs.annotate(
            total_bought_ann=Coalesce(Subquery(bought_sub), 0),
            total_sold_ann=Coalesce(Subquery(sold_sub), 0),
        )

    def show_stock(self, obj):
        if hasattr(obj, "total_bought_ann"):
            stock = obj.total_bought_ann - obj.total_sold_ann
        else:
            stock = obj.current_stock

        if stock <= 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>', "OUT OF STOCK"
            )

        elif stock < 3:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{} (Low)</span>', stock
            )
        return stock

    show_stock.short_description = "Stock"
    show_stock.admin_order_field = "total_bought_ann"

    def show_profit(self, obj):
        return obj.current_sell_price - obj.current_buy_price

    show_profit.short_description = "Profit/Pair"

    def quick_restock_5(self, request, queryset):
        count = 0
        for product in queryset:
            RestockBatch.objects.create(product=product, quantity_added=5)
            count += 1
        self.message_user(request, f"Added 5 stock to {count} products.")

    quick_restock_5.short_description = "Quick Add Stock (+5 Pairs)"


@admin.register(RestockBatch)
class RestockBatchAdmin(ModelAdmin):
    list_display = ("product", "quantity_added", "supplier", "date_added")
    list_filter = ("date_added", "supplier")
    search_fields = ("product__name",)


class SaleItemInline(TabularInline):  # Using Unfold's Inline
    model = SaleItem
    extra = 1
    autocomplete_fields = ["product"]
    fields = ("product", "quantity", "sale_price_at_moment")


@admin.register(Sale)
class SaleAdmin(ModelAdmin):
    list_display = ("id", "customer", "staff", "total_amount", "date_sold")
    inlines = [SaleItemInline]
    readonly_fields = ("total_amount", "date_sold")
    autocomplete_fields = ["customer"]
    search_fields = ["customer__name", "id"]


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    search_fields = ["name", "phone"]
    list_display = ("name", "phone", "address")


@admin.register(Staff)
class StaffAdmin(ModelAdmin):
    list_display = ("name", "role")


admin.site.register(Category, ModelAdmin)
