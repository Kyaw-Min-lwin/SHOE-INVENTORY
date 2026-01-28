from django.db.models import Sum, F
from .models import Product, Sale, SaleItem


def dashboard_callback(request, context):
    # 1. Total Revenue (This naturally includes discounts because Sale.total_amount is discounted)
    total_revenue = Sale.objects.aggregate(sum=Sum("total_amount"))["sum"] or 0

    # 2. Total Profit Calculation
    # Profit = Total Revenue - Total Cost of Goods Sold (COGS)

    # Calculate Total Cost: Sum(buy_price * quantity) for ALL items sold
    total_cost = (
        SaleItem.objects.aggregate(cost=Sum(F("buy_price_at_moment") * F("quantity")))[
            "cost"
        ]
        or 0
    )

    net_profit = total_revenue - total_cost

    # 3. Low Stock Alerts
    low_stock_count = 0
    for p in Product.objects.all():
        if p.current_stock < 3:
            low_stock_count += 1

    # 4. Pass data to Unfold
    context.update(
        {
            "kpi": [
                {
                    "title": "Total Revenue",
                    "metric": f"${total_revenue:,.2f}",
                    "footer": "Lifetime sales (After Discounts)",
                },
                {
                    "title": "Net Profit",
                    "metric": f"${net_profit:,.2f}",
                    "footer": "Revenue - Cost of Goods",
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
