from django.db.models import Sum
from .models import Product, Sale, SaleItem


def dashboard_callback(request, context):
    # 1. Total Revenue
    total_revenue = Sale.objects.aggregate(sum=Sum("total_amount"))["sum"] or 0

    # 2. Total Profit
    # Logic: Sum of (Sale Price - Buy Price) * Quantity for all sold items
    items = SaleItem.objects.all()
    total_profit = sum(
        [
            (item.sale_price_at_moment - item.buy_price_at_moment) * item.quantity
            for item in items
        ]
    )

    # 3. Low Stock Alerts
    # We check all products. If current_stock < 3, count it.
    low_stock_count = 0
    for p in Product.objects.all():
        if p.current_stock < 3:
            low_stock_count += 1

    # 4. Pass data to Unfold
    # Unfold expects a specific list format for 'kpi'
    context.update(
        {
            "kpi": [
                {
                    "title": "Total Revenue",
                    "metric": f"${total_revenue:,.2f}",
                    "footer": "Lifetime sales volume",
                },
                {
                    "title": "Net Profit",
                    "metric": f"${total_profit:,.2f}",
                    "footer": "Total earnings (Revenue - Cost)",
                },
                {
                    "title": "Low Stock Alerts",
                    "metric": str(low_stock_count),
                    "footer": "Products with < 3 items left",
                },
            ],
        }
    )

    return context
