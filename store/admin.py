from django.contrib import admin
from django.db.models import Sum, OuterRef, Subquery, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils.html import format_html, format_html_join
from django.contrib.auth.models import Group
from unfold.contrib.filters.admin import RangeDateFilter

# IMPORT UNFOLD ADMIN
from unfold.admin import ModelAdmin, TabularInline

from .models import Product, Category, RestockBatch, Customer, Sale, SaleItem, Staff

admin.site.unregister(Group)


@admin.register(Product)
class ProductAdmin(ModelAdmin):  # Using Unfold's ModelAdmin
    list_display = (
        "code",
        "name",
        "size",
        "color",
        "gender",
        "origin",
        "pairs_per_bag",
        "pairs_per_box",
        "show_stock",
        "current_buy_price",
        "current_sell_price",
        "show_profit",
    )
    list_editable = (
        "current_sell_price",
        "current_buy_price",
        "pairs_per_bag",
        "pairs_per_box",
    )
    search_fields = ("code", "name", "color", "size")
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
    change_list_template = "admin/store/restockbatch/change_list.html"

    class Media:
        css = {"all": ("store/admin_fixes.css",)}

    list_display = (
        "product",
        "quantity",
        "unit",
        "quantity_added",
        "supplier",
        "date_added",
    )
    list_filter_submit = True
    list_filter = ("unit", ("date_added", RangeDateFilter), "supplier")
    search_fields = ("product__name", "product__code")

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data") and "cl" in response.context_data:
            cl = response.context_data["cl"]
            queryset = cl.queryset

            # KPI 1: Total Pairs Added
            total_pairs = queryset.aggregate(sum=Sum("quantity_added"))["sum"] or 0

            # KPI 2: Total Cost (Quantity Added * Cost Per Pair)
            # Uses Coalesce to handle cases where cost_per_pair might be empty
            total_spend = (
                queryset.aggregate(
                    cost=Sum(
                        F("quantity_added")
                        * Coalesce(
                            F("cost_per_pair"), Value(0), output_field=DecimalField()
                        )
                    )
                )["cost"]
                or 0
            )

            # KPI 3: Count
            batch_count = queryset.count()

            response.context_data["kpi"] = [
                {
                    "title": "Total Stock Added",
                    "metric": f"{total_pairs:,} pairs",
                    "footer": "Inventory volume added",
                    "color": "blue-600",
                },
                {
                    "title": "Total Spend",
                    "metric": f"${total_spend:,.2f}",
                    "footer": "Cost of goods",
                    "color": "rose-600",
                },
                {
                    "title": "Restock Events",
                    "metric": str(batch_count),
                    "footer": "Number of batches",
                    "color": "gray-600",
                },
            ]

        return response


class SaleItemInline(TabularInline):
    model = SaleItem
    extra = 1
    autocomplete_fields = ["product"]
    # We allow editing quantity/unit/price here
    fields = ("product", "quantity", "unit", "sale_price_at_moment")

    class Media:
        css = {"all": ("store/admin2.css",)}


@admin.register(Sale)
class SaleAdmin(ModelAdmin):
    change_list_template = "admin/store/sale/change_list.html"
    list_display = (
        "date_sold",
        "customer",
        "staff",
        "receipt_details",
        "discount_info",
        "total_amount",
        "net_profit",
    )

    # Loads the CSS Fix
    class Media:
        css = {"all": ("store/admin_fixes.css",)}

    inlines = [SaleItemInline]
    readonly_fields = ("total_amount", "date_sold")
    fields = ("customer", "staff", "discount_percentage", "total_amount", "date_sold")

    autocomplete_fields = ["customer"]

    search_fields = [
        "customer__name",
        "id",
        "items__product__code",
        "items__product__name",
    ]
    list_filter_submit = True

    list_filter = (("date_sold", RangeDateFilter), "staff")

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        # We check if the response has context_data (it's a TemplateResponse)
        # 'cl' is the ChangeList object which holds the filtered queryset
        if hasattr(response, "context_data") and "cl" in response.context_data:
            cl = response.context_data["cl"]
            queryset = cl.queryset

            # 1. Total Revenue: Sum of 'total_amount' of visible sales
            total_revenue = queryset.aggregate(sum=Sum("total_amount"))["sum"] or 0

            # 2. Total Cost: Sum of 'buy_price * quantity' for all items inside these sales
            # We filter SaleItems where the sale is in our current filtered list
            total_cost = (
                SaleItem.objects.filter(sale__in=queryset).aggregate(
                    cost=Sum(F("buy_price_at_moment") * F("quantity"))
                )["cost"]
                or 0
            )

            net_profit = total_revenue - total_cost

            # 3. Items Count: Total units sold in these sales
            total_items = (
                SaleItem.objects.filter(sale__in=queryset).aggregate(
                    count=Sum("quantity")
                )["count"]
                or 0
            )

            # Inject into Unfold's KPI context
            # This automatically renders the 3 boxes at the top
            response.context_data["kpi"] = [
                {
                    "title": "Total Revenue",
                    "metric": f"${total_revenue:,.2f}",
                    "footer": "Based on current filters",
                    "color": "emerald-600",
                },
                {
                    "title": "Net Profit",
                    "metric": f"${net_profit:,.2f}",
                    "footer": "Revenue - Cost",
                    "color": "emerald-600",
                },
                {
                    "title": "Total Items Sold",
                    "metric": str(total_items),
                    "footer": "Total units in displayed sales",
                    "color": "blue-600",
                },
            ]

        return response

    def discount_info(self, obj):
        if obj.discount_percentage > 0:
            return format_html(
                "<span style='color: #c9a227; font-weight: bold;'>{}% OFF</span>",
                obj.discount_percentage,
            )
        return "-"

    discount_info.short_description = "Discount"

    def receipt_details(self, obj):
        return format_html(
            "<ul style='margin:0; padding-left:15px; list-style-type:none;'>{}</ul>",
            format_html_join(
                "",
                (
                    "<li style='margin-bottom:4px; border-bottom:1px dashed #eee; padding-bottom:2px;'>"
                    "<strong>#{}</strong> {}<br>"
                    "<span style='font-size:11px;'>"
                    "Qty: {} • "
                    "<span style='color:#666;'>Buy: ${}</span> | "
                    "<strong>Sell: ${}</strong>"
                    "</span></li>"
                ),
                (
                    (
                        item.product.code,
                        item.product.name,
                        f"{item.quantity} {item.get_unit_display()}",
                        item.buy_price_at_moment,
                        item.sale_price_at_moment,
                    )
                    for item in obj.items.all()
                ),
            ),
        )

    receipt_details.short_description = "Product Details"

    def net_profit(self, obj):
        total_cost = sum(
            item.buy_price_at_moment * item.quantity for item in obj.items.all()
        )
        total_revenue = obj.total_amount
        profit = total_revenue - total_cost

        color = "green" if profit >= 0 else "red"
        return format_html(
            "<span style='color: {}; font-weight: bold;'>${}</span>",
            color,
            f"{profit:,.2f}",
        )

    net_profit.short_description = "Profit"


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    search_fields = ["name", "phone"]
    list_display = ("name", "phone", "address")


@admin.register(Staff)
class StaffAdmin(ModelAdmin):
    list_display = ("name", "role")


admin.site.register(Category, ModelAdmin)
