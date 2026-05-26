import os
from app import create_app
from models import db, User, Product, Customer, Sale, Inventory
from datetime import datetime, timedelta
import random

app = create_app()

def populate_db():
    with app.app_context():
        # Clean db
        db.drop_all()
        db.create_all()

        # Create Admin
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)

        # Create Products
        categories = ['Electronics', 'Clothing', 'Home', 'Toys']
        products = []
        for i in range(1, 11):
            p = Product(
                product_name=f'Product {i}',
                category=random.choice(categories),
                price=round(random.uniform(10.0, 500.0), 2),
                stock_quantity=random.randint(5, 50)
            )
            products.append(p)
            db.session.add(p)
            
            # Add inventory record
            inv = Inventory(
                product=p,
                stock_level=p.stock_quantity,
                restock_threshold=10
            )
            db.session.add(inv)

        # Create Customers
        customers = []
        genders = ['Male', 'Female']
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
        for i in range(1, 6):
            c = Customer(
                customer_name=f'Customer {i}',
                age=random.randint(18, 65),
                gender=random.choice(genders),
                city=random.choice(cities)
            )
            customers.append(c)
            db.session.add(c)
            
        db.session.commit()

        # Create Sales
        for _ in range(30):
            p = random.choice(products)
            c = random.choice(customers)
            qty = random.randint(1, 3)
            
            # Reduce inventory
            if p.stock_quantity >= qty:
                p.stock_quantity -= qty
                p.inventory.stock_level -= qty
            
                payment_methods = ['Cash', 'Paytm', 'UPI', 'Card', 'Net Banking', 'Other']
                sale = Sale(
                    product_id=p.id,
                    customer_id=c.id,
                    quantity=qty,
                    total_price=p.price * qty,
                    payment_type=random.choice(payment_methods),
                    sale_date=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                )
                db.session.add(sale)

        db.session.commit()
        print("Database populated successfully!")

if __name__ == '__main__':
    populate_db()


