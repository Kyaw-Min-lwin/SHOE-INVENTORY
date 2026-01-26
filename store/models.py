from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from cloudinary.models import CloudinaryField


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50, blank=True)
    current_buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = CloudinaryField("image", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.size})"

    @property
    def current_stock(self):
        total_bought = (
            self.restockbatch_set.aggregate(total=Sum("quantity_added"))["total"] or 0
        )
        total_sold = self.saleitem_set.aggregate(total=Sum("quantity"))["total"] or 0
        return total_bought - total_sold


class RestockBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    supplier = models.CharField(max_length=100, blank=True)
    cost_per_pair = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Restock Batches"

    def __str__(self):
        return f"Added {self.quantity_added} to {self.product.name}"


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Staff(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, default="Staff")

    class Meta:
        verbose_name_plural = "Staff Members"

    def __str__(self):
        return self.name


class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)
    date_sold = models.DateTimeField(auto_now_add=True)
    # This field is auto-calculated by the signal below
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )

    def __str__(self):
        return f"Sale #{self.id} - {self.date_sold.strftime('%Y-%m-%d')}"

    def update_total(self):
        total = (
            self.items.aggregate(
                total=Sum(models.F("sale_price_at_moment") * models.F("quantity"))
            )["total"]
            or 0
        )
        self.total_amount = total
        self.save(update_fields=["total_amount"])


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    sale_price_at_moment = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True
    )
    buy_price_at_moment = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.sale_price_at_moment:
            self.sale_price_at_moment = self.product.current_sell_price
        if not self.buy_price_at_moment:
            self.buy_price_at_moment = self.product.current_buy_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# --- AUTOMATION SIGNALS ---
@receiver(post_save, sender=SaleItem)
@receiver(post_delete, sender=SaleItem)
def update_sale_total(sender, instance, **kwargs):
    if instance.sale:
        instance.sale.update_total()
