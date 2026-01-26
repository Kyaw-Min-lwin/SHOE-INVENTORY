from django.urls import path
from . import views

urlpatterns = [
    # Homepage (The Catalog)
    path("", views.product_list, name="product_list"),
    # Detail Page (e.g., /product/5/)
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
]
