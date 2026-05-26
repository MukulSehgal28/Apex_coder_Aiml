from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, send_file
from flask_login import current_user, login_user, logout_user, login_required
from sqlalchemy import func, extract
from models import db, User, Product, Customer, Sale, Inventory
from forms import LoginForm, RegistrationForm, ProductForm, CustomerForm, SaleForm, InventoryForm
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import io
import datetime
import pytz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import joblib

# --- MACHINE LEARNING MODEL INTEGRATION ---
# Model Loading:
# Load the trained Linear Regression model globally (once) at application startup.
# We resolve the path robustly by checking absolute path relative to this script first,
# then falling back to direct path as requested.
sales_model = None
try:
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'sales_prediction_model.pkl')
    if os.path.exists(model_path):
        sales_model = joblib.load(model_path)
    else:
        sales_model = joblib.load('ml_models/sales_prediction_model.pkl')
except Exception as e:
    print("MODEL ERROR:", str(e))

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # Metrics
    total_revenue = db.session.query(func.sum(Sale.total_price)).scalar() or 0
    total_orders = Sale.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    low_stock = Inventory.query.filter(Inventory.stock_level <= Inventory.restock_threshold).count()

    # Advanced Insights
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    best_product = db.session.query(Product.product_name, func.sum(Sale.quantity).label('total_qty')).join(Sale).group_by(Product.id).order_by(func.sum(Sale.quantity).desc()).first()
    best_product_name = best_product.product_name if best_product else 'N/A'

    top_cust = db.session.query(Customer.customer_name, func.sum(Sale.total_price).label('spent')).join(Sale).group_by(Customer.id).order_by(func.sum(Sale.total_price).desc()).first()
    top_customer_name = top_cust.customer_name if top_cust else 'N/A'

    most_used_payment = db.session.query(Sale.payment_type, func.count(Sale.id)).group_by(Sale.payment_type).order_by(func.count(Sale.id).desc()).first()
    popular_payment = most_used_payment[0] if most_used_payment else 'N/A'

    generate_charts()

    return render_template('dashboard.html', title='Dashboard', 
                           total_revenue=total_revenue, 
                           total_orders=total_orders,
                           total_customers=total_customers,
                           total_products=total_products,
                           low_stock=low_stock,
                           avg_order_value=avg_order_value,
                           best_product=best_product_name,
                           top_customer=top_customer_name,
                           popular_payment=popular_payment)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Congratulations, you are now a registered user!', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash('Error registering user.', 'danger')
    return render_template('register.html', title='Register', form=form)

# --- PRODUCTS CRUD ---
@bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    products = Product.query.all()
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(product_name=form.product_name.data, category=form.category.data, 
                          price=form.price.data, stock_quantity=form.stock_quantity.data)
        db.session.add(product)
        try:
            db.session.commit()
            inv = Inventory(product_id=product.id, stock_level=product.stock_quantity, restock_threshold=10)
            db.session.add(inv)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('main.products'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding product.', 'danger')
    return render_template('products.html', title='Products', products=products, form=form)

@bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.product_name = form.product_name.data
        product.category = form.category.data
        product.price = form.price.data
        product.stock_quantity = form.stock_quantity.data
        try:
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('main.products'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating product.', 'danger')
    return render_template('products.html', title='Edit Product', products=Product.query.all(), form=form, edit_id=id)

@bp.route('/products/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        # Also delete associated inventory and sales to maintain referential integrity
        if product.inventory:
            db.session.delete(product.inventory)
        Sale.query.filter_by(product_id=product.id).delete()
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product.', 'danger')
    return redirect(url_for('main.products'))

# --- CUSTOMERS CRUD ---
@bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    customers = Customer.query.all()
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(customer_name=form.customer_name.data, age=form.age.data,
                            gender=form.gender.data, city=form.city.data)
        db.session.add(customer)
        try:
            db.session.commit()
            flash('Customer added successfully!', 'success')
            return redirect(url_for('main.customers'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding customer.', 'danger')
    return render_template('customers.html', title='Customers', customers=customers, form=form)

@bp.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        customer.customer_name = form.customer_name.data
        customer.age = form.age.data
        customer.gender = form.gender.data
        customer.city = form.city.data
        try:
            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('main.customers'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating customer.', 'danger')
    return render_template('customers.html', title='Edit Customer', customers=Customer.query.all(), form=form, edit_id=id)

@bp.route('/customers/delete/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        Sale.query.filter_by(customer_id=customer.id).delete()
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting customer.', 'danger')
    return redirect(url_for('main.customers'))

# --- SALES CRUD ---
@bp.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    form = SaleForm()
    form.product_id.choices = [(p.id, p.product_name) for p in Product.query.all()]
    form.customer_id.choices = [(c.id, c.customer_name) for c in Customer.query.all()]
    
    if form.validate_on_submit():
        product = Product.query.get(form.product_id.data)
        inventory = Inventory.query.filter_by(product_id=product.id).first()
        
        if inventory and inventory.stock_level >= form.quantity.data:
            total_price = product.price * form.quantity.data
            sale = Sale(product_id=product.id, customer_id=form.customer_id.data,
                        quantity=form.quantity.data, total_price=total_price, payment_type=form.payment_type.data)
            
            inventory.stock_level -= form.quantity.data
            product.stock_quantity -= form.quantity.data
            
            db.session.add(sale)
            try:
                db.session.commit()
                flash('Sale recorded successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error recording sale.', 'danger')
        else:
            flash('Not enough stock available!', 'danger')
        return redirect(url_for('main.sales'))
    return render_template('sales.html', title='Sales', sales=sales, form=form)

@bp.route('/sales/delete/<int:id>', methods=['POST'])
@login_required
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    try:
        # Restore inventory
        inventory = Inventory.query.filter_by(product_id=sale.product_id).first()
        if inventory:
            inventory.stock_level += sale.quantity
            inventory.product.stock_quantity += sale.quantity
        db.session.delete(sale)
        db.session.commit()
        flash('Sale deleted and inventory restored.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting sale.', 'danger')
    return redirect(url_for('main.sales'))

# --- INVENTORY CRUD ---
@bp.route('/inventory')
@login_required
def inventory():
    items = Inventory.query.join(Product).all()
    return render_template('inventory.html', title='Inventory', items=items)

@bp.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_inventory(id):
    item = Inventory.query.get_or_404(id)
    form = InventoryForm(obj=item)
    if form.validate_on_submit():
        item.stock_level = form.stock_level.data
        item.restock_threshold = form.restock_threshold.data
        item.product.stock_quantity = form.stock_level.data
        try:
            db.session.commit()
            flash('Inventory updated successfully!', 'success')
            return redirect(url_for('main.inventory'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating inventory.', 'danger')
    return render_template('inventory_edit.html', title='Edit Inventory', form=form, item=item)


# --- REPORTS & DOWNLOADS ---
@bp.route('/reports')
@login_required
def reports():
    return render_template('reports.html', title='Reports')

@bp.route('/reports/download/<type>/<format>')
@login_required
def download_report(type, format):
    # Fetch Data
    ist_now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
    filename = f"{type}_report_{ist_now.strftime('%Y%m%d')}"
    
    if type == 'revenue':
        sales = db.session.query(Sale.sale_date, Sale.total_price, Sale.payment_type).all()
        # Format dates in IST
        sales = [(s.sale_date.strftime('%d %b %Y, %I:%M %p '), s.total_price, s.payment_type) for s in sales]
        df = pd.DataFrame(sales, columns=['Date', 'Revenue', 'Payment Method'])
    elif type == 'product':
        products = db.session.query(Product.id, Product.product_name, Product.category, Product.price, Product.stock_quantity).all()
        df = pd.DataFrame(products, columns=['ID', 'Product Name', 'Category', 'Price', 'Stock'])
    elif type == 'customer':
        customers = db.session.query(Customer.id, Customer.customer_name, Customer.age, Customer.city).all()
        df = pd.DataFrame(customers, columns=['ID', 'Name', 'Age', 'City'])
    elif type == 'inventory':
        inventory = db.session.query(Product.product_name, Inventory.stock_level, Inventory.restock_threshold).join(Inventory).all()
        df = pd.DataFrame(inventory, columns=['Product Name', 'Stock Level', 'Restock Threshold'])
    
    # Export Data
    if format == 'csv':
        csv_data = df.to_csv(index=False)
        return send_file(io.BytesIO(csv_data.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f"{filename}.csv")
    elif format == 'xlsx':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f"{filename}.xlsx")
    elif format == 'pdf':
        output = io.BytesIO()
        p = canvas.Canvas(output, pagesize=letter)
        p.drawString(100, 750, f"Shop Insight Hub - {type.capitalize()} Report")
        p.drawString(100, 730, f"Generated on: {ist_now.strftime('%d %b %Y, %I:%M %p IST')}")
        
        y = 700
        headers = list(df.columns)
        header_str = " | ".join(headers)
        p.drawString(50, y, header_str)
        y -= 20
        
        for index, row in df.iterrows():
            if y < 50:
                p.showPage()
                y = 750
            row_str = " | ".join([str(val) for val in row.values])
            p.drawString(50, y, row_str)
            y -= 20
            
        p.save()
        output.seek(0)
        return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=f"{filename}.pdf")

@bp.route('/ai_insights', methods=['GET', 'POST'])
@login_required
def ai_insights():
    """
    AI Insights Route:
    Handles predictive analytics capabilities. Performs live Linear Regression sales forecasting.
    Includes support for future modular integrations like Clustering and Churn models.
    """
    predicted_sales = None
    quantity = 3.0
    price = 500.0
    age = 25.0
    
    # 1. POST Request Handling:
    # Ensure form values are received properly from POST request: quantity, price, age.
    if request.method == 'POST':
        try:
            quantity = float(request.form.get('quantity', 3.0))
            price = float(request.form.get('price', 500.0))
            age = float(request.form.get('age', 25.0))
        except ValueError as e:
            print("ValueError parsing POST form inputs:", str(e))

    # 2. Prediction Pipeline:
    try:
        if sales_model:
            # Ensure prediction input EXACTLY matches training feature names:
            # 'Quantity', 'Price per Unit', 'Age'. Must match the training notebook exactly.
            sample_data = pd.DataFrame({
                'Quantity': [float(quantity)],
                'Price per Unit': [float(price)],
                'Age': [float(age)]
            })
            
            # Ensure predict() is called correctly on the DataFrame and rounded to 2 decimal places
            prediction = sales_model.predict(sample_data)
            predicted_sales = round(prediction[0], 2)
            
            # --- Future ML Expansion Support ---
            # The architecture is designed to be highly modular and production-safe for:
            # - K-Means Clustering (Customer Segmentation based on Age/Spending)
            # - Logistic Regression (Customer Churn Prediction based on Purchase frequency)
            # - Time Series integration (ARIMA/Prophet for forecasting future sales)
        else:
            predicted_sales = "Model Error: Global Linear Regression model is not loaded."
            print("MODEL ERROR: Global sales_model is None")
    except Exception as e:
        print("MODEL ERROR:", str(e))
        predicted_sales = f"Prediction Failed: {str(e)}"

    # Retain exact backward compatibility for variables passed to template (qty, price, age)
    return render_template('ai_insights.html', title='AI Insights', 
                           predicted_sales=predicted_sales, 
                           qty=quantity, 
                           price=price, 
                           age=age)

def generate_charts():
    charts_dir = os.path.join(current_app.root_path, 'static', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    matplotlib.rc('font', family='sans-serif')
    plt.style.use('bmh')

    # 1. Daily Revenue Trend
    sales = db.session.query(func.date(Sale.sale_date).label('date'), func.sum(Sale.total_price).label('revenue')).group_by(func.date(Sale.sale_date)).all()
    if sales:
        df = pd.DataFrame(sales, columns=['Date', 'Revenue'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        plt.figure(figsize=(10,4))
        plt.plot(df['Date'], df['Revenue'], marker='o', linestyle='-', color='#0d6efd', linewidth=2)
        plt.fill_between(df['Date'], df['Revenue'], alpha=0.1, color='#0d6efd')
        plt.title('Daily Revenue Trend')
        plt.xlabel('Date')
        plt.ylabel('Revenue (₹)')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'revenue_trend.png'), dpi=100)
        plt.close()

    # 2. Payment Method Pie Chart
    payments = db.session.query(Sale.payment_type, func.count(Sale.id)).group_by(Sale.payment_type).all()
    if payments:
        labels = [p[0] for p in payments]
        sizes = [p[1] for p in payments]
        colors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6c757d']
        
        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, wedgeprops={'edgecolor': 'w'})
        plt.title('Payment Methods', pad=20)
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'payment_methods.png'), dpi=100)
        plt.close()

    # 3. Top Selling Products
    top_products = db.session.query(Product.product_name, func.sum(Sale.quantity)).join(Sale).group_by(Product.product_name).order_by(func.sum(Sale.quantity).desc()).limit(5).all()
    if top_products:
        names = [p[0] for p in top_products]
        qtys = [p[1] for p in top_products]
        
        plt.figure(figsize=(8,4))
        plt.barh(names[::-1], qtys[::-1], color='#198754')
        plt.title('Top 5 Selling Products')
        plt.xlabel('Quantity Sold')
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'top_products.png'), dpi=100)
        plt.close()
        
    # 4. Monthly Revenue Bar Chart
    monthly_sales = db.session.query(extract('month', Sale.sale_date).label('month'), func.sum(Sale.total_price).label('revenue')).group_by(extract('month', Sale.sale_date)).all()
    if monthly_sales:
        df_m = pd.DataFrame(monthly_sales, columns=['Month', 'Revenue'])
        df_m = df_m.sort_values('Month')
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        df_m['MonthName'] = df_m['Month'].apply(lambda x: month_names[int(x)-1])
        
        plt.figure(figsize=(8,4))
        plt.bar(df_m['MonthName'], df_m['Revenue'], color='#0dcaf0')
        plt.title('Monthly Revenue')
        plt.ylabel('Revenue (₹)')
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'monthly_revenue.png'), dpi=100)
        plt.close()

    # 5. Product Category Pie Chart
    categories = db.session.query(Product.category, func.sum(Sale.quantity)).join(Sale).group_by(Product.category).all()
    if categories:
        labels = [c[0] for c in categories]
        sizes = [c[1] for c in categories]
        colors = ['#ffc107', '#0dcaf0', '#dc3545', '#198754', '#0d6efd', '#6f42c1', '#fd7e14']
        
        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, wedgeprops={'edgecolor': 'w'})
        plt.title('Sales by Category', pad=20)
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'product_categories.png'), dpi=100)
        plt.close()
