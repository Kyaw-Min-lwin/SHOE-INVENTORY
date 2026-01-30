from django.shortcuts import render, get_object_or_404
from .models import Product, Category
from django.db.models import Q


def product_list(request):
    # 1. Get all products
    all_products = Product.objects.all()

    # 2. Filter by Category
    category_id = request.GET.get("category")
    if category_id:
        all_products = all_products.filter(category__id=category_id)

    query = request.GET.get("q")
    if query:
        all_products = all_products.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(color__icontains=query)
        )

    # 3. Separate Stock in Python (since current_stock is a property)
    # This is fine for < 1000 items. For more, we'd use DB annotations.
    available_products = []
    sold_out_products = []

    for p in all_products:
        if p.current_stock > 0:
            available_products.append(p)
        else:
            sold_out_products.append(p)

    # 4. Get categories for sidebar
    categories = Category.objects.all()

    context = {
        "products": available_products,
        "sold_out": sold_out_products,
        "categories": categories,
        "current_category": int(category_id) if category_id else None,
        "search_query": query,
    }
    return render(request, "store/product_list.html", context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 1. Find Related Products (Same category, excluding current one)
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[
        :4
    ]

    # 2. WhatsApp Link
    # Replace with real phone number
    shop_phone = "1234567890"
    text = f"Hi, I'm interested in the {product.name} (Size: {product.size}). Is it available?"
    whatsapp_url = f"https://wa.me/{shop_phone}?text={text}"

    context = {
        "product": product,
        "related_products": related_products,
        "whatsapp_url": whatsapp_url,
    }
    return render(request, "store/product_detail.html", context)
