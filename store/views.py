from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category


def product_list(request):
    """
    The main catalog page.
    Handles searching, category filtering, and stock logic.
    """
    # 1. Start with all products
    products = Product.objects.all()

    # 2. Get search query (e.g. ?q=nike)
    query = request.GET.get("q")
    if query:
        # Search in name, color, OR size
        products = products.filter(
            Q(name__icontains=query)
            | Q(color__icontains=query)
            | Q(size__icontains=query)
        )

    # 3. Get category filter (e.g. ?category=1)
    category_id = request.GET.get("category")
    if category_id:
        products = products.filter(category_id=category_id)

    # 4. Stock Logic: Separate "Available" vs "Sold Out"
    # Note: Since current_stock is a property, we can't filter() by it in SQL easily.
    # We will do a Python list comprehension (efficient enough for <5000 items).
    available_products = [p for p in products if p.current_stock > 0]
    sold_out_products = [p for p in products if p.current_stock <= 0]

    # 5. Context for the template
    context = {
        "products": available_products,  # The ones customers can buy
        "sold_out": sold_out_products,  # Optional: Show at bottom or hide
        "categories": Category.objects.all(),  # For the sidebar filter
        "search_query": query,
    }
    return render(request, "store/product_list.html", context)


def product_detail(request, pk):
    """
    The single product page.
    Shows large image and details.
    """
    product = get_object_or_404(Product, pk=pk)

    # Simple recommendation logic: Show other shoes in same category
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[
        :4
    ]

    context = {"product": product, "related_products": related_products}
    return render(request, "store/product_detail.html", context)
