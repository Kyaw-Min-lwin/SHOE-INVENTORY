import csv
import pandas as pd
from django.core.management.base import BaseCommand
from store.models import Product, Category, RestockBatch

class Command(BaseCommand):
    help = 'Imports old stock from latli stock.csv'

    def handle(self, *args, **kwargs):
        # 1. Read the CSV file using Pandas (Easier to handle NaN/Empty values)
        # Make sure 'latli_stock.csv' is in your main folder (same level as manage.py)
        try:
            df = pd.read_csv('latli_stock.csv')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('File "latli_stock.csv" not found. Please rename your file and put it in the project root.'))
            return

        # 2. Get or Create a default category for these imports
        category, _ = Category.objects.get_or_create(name="Old Stock Import")

        count = 0
        for index, row in df.iterrows():
            # Combine Name and Code to make a unique product name
            # Example: "IQ Kwin (101-02)"
            code = str(row['Code']) if pd.notna(row['Code']) else "No Code"
            name = str(row['Name']) if pd.notna(row['Name']) else "Unknown"
            full_name = f"{name} ({code})"

            # Handle Prices (Default to 0 if missing)
            sell_price = row['Price'] if pd.notna(row['Price']) else 0
            # Your sheet had empty Original Price, so we default to 0
            buy_price = row['Original Price'] if pd.notna(row['Original Price']) else 0

            # Create the Product
            product = Product.objects.create(
                name=full_name,
                category=category,
                size=row['Size'], # Importing the raw string "39-43(39,40...)"
                current_buy_price=buy_price,
                current_sell_price=sell_price,
                color="Unknown" # Your sheet didn't have color
            )

            # Create the Stock Entry
            stock_qty = int(row['Stock']) if pd.notna(row['Stock']) else 0
            if stock_qty > 0:
                RestockBatch.objects.create(
                    product=product,
                    quantity_added=stock_qty,
                    supplier="Initial Import",
                    cost_per_pair=buy_price
                )
            
            count += 1
            self.stdout.write(f"Imported: {full_name}")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} products!'))