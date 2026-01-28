import csv
import pandas as pd
from django.core.management.base import BaseCommand
from store.models import Product, Category, RestockBatch

class Command(BaseCommand):
    help = 'Imports old stock from latli stock.csv'

    def handle(self, *args, **kwargs):
        #  Reading the CSV file using Pandas
        try:
            df = pd.read_csv('latli_stock.csv')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('File "latli_stock.csv" not found. Please rename your file and put it in the project root.'))
            return

        # 2. Get or Create a default category for these imports
        category, _ = Category.objects.get_or_create(name="Old Stock Import")

        count = 0
        for _, row in df.iterrows():
            # All codes are unique
            p_code = str(row["Code"]) if pd.notna(row["Code"]) else "No Code"
            p_name = str(row["Name"]) if pd.notna(row["Name"]) else "Unknown"

            # Handle Prices (Default to 0 if missing)
            sell_price = row['Price'] if pd.notna(row['Price']) else 0
            # Your sheet had empty Original Price, so we default to 0
            buy_price = row['Original Price'] if pd.notna(row['Original Price']) else 0
            p_color = row["Color"] if pd.notna(row["Color"]) else "Black"
            p_gender = row["Gender"] if pd.notna(row["Gender"]) else "Male"
            p_origin = row["Origin"] if pd.notna(row["Origin"]) else "India"
            p_per_bag = row["Pairs per Bag"] if pd.notna(row["Pairs per Bag"]) else 0
            p_per_box = row["Pairs per Box"] if pd.notna(row["Pairs per Box"]) else 0

            # Create the Product
            product = Product.objects.create(
                name=p_name,
                code=p_code,
                category=category,
                size=row["Size"],  # Importing the raw string "39-43(39,40...)"
                current_buy_price=buy_price,
                current_sell_price=sell_price,
                color=p_color,
                gender=p_gender,
                origin=p_origin,
                pairs_per_bag=p_per_bag,
                pairs_per_box=p_per_box,
            )

            # Create the Stock Entry
            stock_qty = int(row['Stock']) if pd.notna(row['Stock']) else 0
            supplier = (
                row["Supplier"] if pd.notna(row["Supplier"]) else "Initial Import"
            )
            if stock_qty > 0:
                RestockBatch.objects.create(
                    product=product,
                    quantity_added=stock_qty,
                    supplier=supplier,
                    cost_per_pair=buy_price,
                )

            count += 1
            self.stdout.write(f"Imported: {p_name}")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} products!'))
