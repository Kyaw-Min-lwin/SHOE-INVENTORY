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
    code = models.CharField(max_length=50)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=50, blank=True)
    origin = models.CharField(max_length=50, blank=True)
    current_buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    pairs_per_bag = models.IntegerField(blank=True, null=True)
    pairs_per_box = models.IntegerField(blank=True, null=True)
    image = CloudinaryField("image", blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def current_stock(self):
        total_bought = (
            self.restockbatch_set.aggregate(total=Sum("quantity_added"))["total"] or 0
        )
        total_sold = self.saleitem_set.aggregate(total=Sum("quantity"))["total"] or 0
        return total_bought - total_sold


class RestockBatch(models.Model):
    UNIT_PAIRS = "pairs"
    UNIT_BAGS = "bags"
    UNIT_BOXES = "boxes"

    UNIT_CHOICES = [
        (UNIT_PAIRS, "Pairs"),
        (UNIT_BAGS, "Bags"),
        (UNIT_BOXES, "Boxes"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(
        help_text="Number of units added (pairs / bags / boxes)"
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_PAIRS,
    )
    quantity_added = models.PositiveIntegerField(
        editable=False,
        help_text="Total pairs added (auto-calculated)",
    )
    supplier = models.CharField(max_length=100, blank=True)
    cost_per_pair = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Restock Batches"

    def save(self, *args, **kwargs):
        if self.unit == self.UNIT_PAIRS:
            self.quantity_added = self.quantity

        elif self.unit == self.UNIT_BAGS:
            if not self.product.pairs_per_bag:
                raise ValueError("Product has no pairs_per_bag defined")
            self.quantity_added = self.quantity * self.product.pairs_per_bag

        elif self.unit == self.UNIT_BOXES:
            if not self.product.pairs_per_box:
                raise ValueError("Product has no pairs_per_box defined")
            self.quantity_added = self.quantity * self.product.pairs_per_box

        super().save(*args, **kwargs)

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

    # NEW: Discount Field
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Enter percentage (e.g. 10 for 10% off)",
    )

    # This field is auto-calculated by the signal/save method
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )

    def __str__(self):
        return f"Sale #{self.id} - {self.date_sold.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Only calculate if the sale already has items (exists in DB)
        if self.pk:
            subtotal = (
                self.items.aggregate(
                    total=Sum(models.F("sale_price_at_moment") * models.F("quantity"))
                )["total"]
                or 0
            )

            # Apply Discount logic
            if self.discount_percentage > 0:
                discount_amount = subtotal * (self.discount_percentage / 100)
                self.total_amount = subtotal - discount_amount
            else:
                self.total_amount = subtotal

        super().save(*args, **kwargs)

    def update_total(self):
        # Triggered by signals from SaleItem
        # We just call save(), which handles the recalculation logic above
        self.save()


class SaleItem(models.Model):
    UNIT_PAIRS = "pairs"
    UNIT_BAGS = "bags"
    UNIT_BOXES = "boxes"

    UNIT_CHOICES = [
        (UNIT_PAIRS, "Pairs"),
        (UNIT_BAGS, "Bags"),
        (UNIT_BOXES, "Boxes"),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_PAIRS,
    )

    quantity = models.PositiveIntegerField(
        help_text="Number of units added (pairs / bags / boxes)", default=1
    )
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

        # Scaling logic for Bags/Boxes
        if self.unit == self.UNIT_BAGS:
            if not self.product.pairs_per_bag:
                raise ValueError("Product has no pairs_per_bag defined")
            # Multiply price by pairs per bag (assuming price is PER PAIR)
            # OR if price is PER BAG, logic changes.
            # Assuming current_sell_price is PER PAIR:
            # But wait, usually price is per unit.
            # If I sell 1 BAG, the price should be Pairs * UnitPrice.
            # Your logic previously was:
            self.sale_price_at_moment = (
                self.product.pairs_per_bag * self.sale_price_at_moment
            )
            # Also scale buy price so profit calculation is correct per unit sold
            self.buy_price_at_moment = (
                self.product.pairs_per_bag * self.buy_price_at_moment
            )

        elif self.unit == self.UNIT_BOXES:
            if not self.product.pairs_per_box:
                raise ValueError("Product has no pairs_per_box defined")
            self.sale_price_at_moment = (
                self.product.pairs_per_box * self.sale_price_at_moment
            )
            self.buy_price_at_moment = (
                self.product.pairs_per_box * self.buy_price_at_moment
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# --- AUTOMATION SIGNALS ---
@receiver(post_save, sender=SaleItem)
@receiver(post_delete, sender=SaleItem)
def update_sale_total(sender, instance, **kwargs):
    if instance.sale:
        instance.sale.update_total()
