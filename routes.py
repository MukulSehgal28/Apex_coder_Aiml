from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, send_file, session
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
# Load the trained Linear and Logistic Regression models globally (once) at application startup.
# We resolve the paths robustly by checking absolute paths relative to this script first,
# then falling back to direct paths and relative parent configurations.
sales_model = None
try:
    model_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'sales_prediction_model.pkl'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ml_models', 'sales_prediction_model.pkl'),
        'ml_models/sales_prediction_model.pkl',
        '../ml_models/sales_prediction_model.pkl'
    ]
    for p in model_paths:
        if os.path.exists(p):
            sales_model = joblib.load(p)
            print(f"Successfully loaded Linear Regression model from: {p}")
            break
    if sales_model is None:
        sales_model = joblib.load('ml_models/sales_prediction_model.pkl')
except Exception as e:
    print("MODEL ERROR loading sales_prediction_model:", str(e))

logistic_sales_model = None
try:
    logistic_model_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'logistic_sales_model.pkl'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ml_models', 'logistic_sales_model.pkl'),
        'ml_models/logistic_sales_model.pkl',
        '../ml_models/logistic_sales_model.pkl'
    ]
    for p in logistic_model_paths:
        if os.path.exists(p):
            logistic_sales_model = joblib.load(p)
            print(f"Successfully loaded Logistic Regression model from: {p}")
            break
    if logistic_sales_model is None:
        logistic_sales_model = joblib.load('ml_models/logistic_sales_model.pkl')
except Exception as e:
    print("LOGISTIC MODEL ERROR loading logistic_sales_model:", str(e))

kmeans_model = None
try:
    kmeans_model_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'kmeans_model.pkl'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ml_models', 'kmeans_model.pkl'),
        'ml_models/kmeans_model.pkl',
        '../ml_models/kmeans_model.pkl'
    ]
    for p in kmeans_model_paths:
        if os.path.exists(p):
            kmeans_model = joblib.load(p)
            print(f"Successfully loaded K-Means model from: {p}")
            break
    if kmeans_model is None:
        kmeans_model = joblib.load('ml_models/kmeans_model.pkl')
except Exception as e:
    print("K-MEANS MODEL ERROR loading kmeans_model:", str(e))

arima_sales_model = None
arima_load_error = None
try:
    arima_model_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'arima_sales_model.pkl'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ml_models', 'arima_sales_model.pkl'),
        'ml_models/arima_sales_model.pkl',
        '../ml_models/arima_sales_model.pkl'
    ]
    for p in arima_model_paths:
        if os.path.exists(p):
            arima_sales_model = joblib.load(p)
            print(f"Successfully loaded ARIMA model from: {p}")
            print("ARIMA model loaded successfully")
            break
    if arima_sales_model is None:
        arima_sales_model = joblib.load('ml_models/arima_sales_model.pkl')
        print("ARIMA model loaded successfully")
except Exception as e:
    arima_load_error = str(e)
    print("ARIMA MODEL ERROR loading arima_sales_model:", arima_load_error)

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
    Handles predictive analytics capabilities. Performs live Linear and Logistic Regression,
    and K-Means Customer Segmentation. Saves state in the session to prevent predictions from clearing other cards' results.
    """
    # Load all variables from session or set defaults
    predicted_sales = session.get('predicted_sales', None)
    qty_lin = session.get('qty_lin', 3.0)
    price_lin = session.get('price_lin', 500.0)
    age_lin = session.get('age_lin', 25.0)

    predicted_class = session.get('predicted_class', None)
    qty_log = session.get('qty_log', 3.0)
    price_log = session.get('price_log', 500.0)
    age_log = session.get('age_log', 25.0)
    gender_log = session.get('gender_log', 1)
    category_log = session.get('category_log', 2)

    predicted_cluster = session.get('predicted_cluster', None)
    spending_kmeans = session.get('spending_kmeans', 1000.0)
    frequency_kmeans = session.get('frequency_kmeans', 5.0)
    discount_kmeans = session.get('discount_kmeans', 15.0)
    quantity_kmeans = session.get('quantity_kmeans', 10.0)

    arima_forecast_active = session.get('arima_forecast_active', False)
    arima_forecast_val = session.get('arima_forecast_val', None)
    arima_model_name = session.get('arima_model_name', 'ARIMA(1,1,1)')
    arima_rows = session.get('arima_rows', 1377)
    arima_years = session.get('arima_years', '2020–2023')
    arima_points = session.get('arima_points', 48)
    arima_mape = session.get('arima_mape', '28.16%')
    arima_accuracy = session.get('arima_accuracy', '71.84%')
    arima_error = session.get('arima_error', None)
    forecast_months = session.get('forecast_months', 12)

    if arima_sales_model is None and arima_load_error is not None:
        arima_error = f"ARIMA Model Load Error: {arima_load_error}"

    arima_chart_exists = False
    if arima_forecast_active:
        arima_chart_path = os.path.join(current_app.root_path, 'static', 'charts', 'arima_forecast.png')
        if os.path.exists(arima_chart_path):
            arima_chart_exists = True

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'linear':
            try:
                qty_val = request.form.get('quantity')
                price_val = request.form.get('price')
                age_val = request.form.get('age')

                if qty_val is None or qty_val == '' or price_val is None or price_val == '' or age_val is None or age_val == '':
                    flash('All inputs are required for Linear Regression prediction.', 'warning')
                else:
                    qty_lin = float(qty_val)
                    price_lin = float(price_val)
                    age_lin = float(age_val)

                    # Save input values in session
                    session['qty_lin'] = qty_lin
                    session['price_lin'] = price_lin
                    session['age_lin'] = age_lin

                    if sales_model:
                        sample_data = pd.DataFrame({
                            'Quantity': [qty_lin],
                            'Price per Unit': [price_lin],
                            'Age': [age_lin]
                        })
                        prediction = sales_model.predict(sample_data)
                        predicted_sales = round(prediction[0], 2)
                        session['predicted_sales'] = predicted_sales
                    else:
                        predicted_sales = "Model Error: Global Linear Regression model is not loaded."
                        session['predicted_sales'] = predicted_sales
            except ValueError as e:
                flash('Please enter valid numeric inputs for Linear Regression prediction.', 'danger')
                print("ValueError in Linear Form:", str(e))
            except Exception as e:
                predicted_sales = f"Prediction Failed: {str(e)}"
                session['predicted_sales'] = predicted_sales
                print("Linear prediction exception:", str(e))

        elif form_type == 'logistic':
            try:
                qty_val = request.form.get('quantity')
                price_val = request.form.get('price')
                age_val = request.form.get('age')
                gender_val = request.form.get('gender')
                category_val = request.form.get('category')

                print(f"DEBUG LOGISTIC FORM INPUTS - qty: {qty_val}, price: {price_val}, age: {age_val}, gender: {gender_val}, category: {category_val}")

                if (qty_val is None or str(qty_val).strip() == '' or 
                    price_val is None or str(price_val).strip() == '' or 
                    age_val is None or str(age_val).strip() == '' or 
                    gender_val is None or str(gender_val).strip() == '' or 
                    category_val is None or str(category_val).strip() == ''):
                    flash('All inputs are required for Logistic Regression prediction.', 'warning')
                    predicted_class = "Error: Missing input fields"
                    session['predicted_class'] = predicted_class
                else:
                    qty_log = float(str(qty_val).strip())
                    price_log = float(str(price_val).strip())
                    age_log = float(str(age_val).strip())
                    gender_log = int(float(str(gender_val).strip()))
                    category_log = int(float(str(category_val).strip()))

                    # Save input values in session
                    session['qty_log'] = qty_log
                    session['price_log'] = price_log
                    session['age_log'] = age_log
                    session['gender_log'] = gender_log
                    session['category_log'] = category_log

                    if logistic_sales_model is not None:
                        prediction_input = [[qty_log, price_log, age_log, gender_log, category_log]]
                        prediction = logistic_sales_model.predict(prediction_input)
                        predicted_class = int(prediction[0])
                        session['predicted_class'] = predicted_class
                        print(f"DEBUG LOGISTIC PREDICTION RESULT: {predicted_class}")
                    else:
                        predicted_class = "Model Error: Global Logistic Regression model failed to load at startup."
                        session['predicted_class'] = predicted_class
                        print("LOGISTIC MODEL ERROR: Global logistic_sales_model is None")
            except ValueError as e:
                predicted_class = f"Value Conversion Error: {str(e)}"
                session['predicted_class'] = predicted_class
                flash(f'Please enter valid numeric inputs: {str(e)}', 'danger')
                print("ValueError in Logistic Form:", str(e))
            except Exception as e:
                predicted_class = f"Prediction Error: {str(e)}"
                session['predicted_class'] = predicted_class
                flash(f'Prediction failed: {str(e)}', 'danger')
                print("Logistic prediction exception:", str(e))

        elif form_type == 'kmeans':
            try:
                spending_val = request.form.get('spending')
                freq_val = request.form.get('frequency')
                discount_val = request.form.get('discount')
                qty_val = request.form.get('quantity')

                print(f"DEBUG KMEANS FORM INPUTS - spending: {spending_val}, frequency: {freq_val}, discount: {discount_val}, quantity: {qty_val}")

                if (spending_val is None or str(spending_val).strip() == '' or 
                    freq_val is None or str(freq_val).strip() == '' or 
                    discount_val is None or str(discount_val).strip() == '' or 
                    qty_val is None or str(qty_val).strip() == ''):
                    flash('All inputs are required for Customer Segmentation prediction.', 'warning')
                    predicted_cluster = "Error: Missing input fields"
                    session['predicted_cluster'] = predicted_cluster
                else:
                    spending_kmeans = float(str(spending_val).strip())
                    frequency_kmeans = float(str(freq_val).strip())
                    discount_kmeans = float(str(discount_val).strip())
                    quantity_kmeans = float(str(qty_val).strip())

                    # Save input values in session
                    session['spending_kmeans'] = spending_kmeans
                    session['frequency_kmeans'] = frequency_kmeans
                    session['discount_kmeans'] = discount_kmeans
                    session['quantity_kmeans'] = quantity_kmeans

                    if kmeans_model is not None:
                        sample_data = pd.DataFrame({
                            'Total_Spending': [spending_kmeans],
                            'Purchase_Frequency': [frequency_kmeans],
                            'Avg_Discount': [discount_kmeans],
                            'Total_Quantity': [quantity_kmeans]
                        })
                        prediction = kmeans_model.predict(sample_data)
                        predicted_cluster = int(prediction[0])
                        session['predicted_cluster'] = predicted_cluster
                        print(f"DEBUG KMEANS PREDICTION RESULT: {predicted_cluster}")
                    else:
                        predicted_cluster = "Model Error: Global K-Means model failed to load at startup."
                        session['predicted_cluster'] = predicted_cluster
                        print("KMEANS MODEL ERROR: Global kmeans_model is None")
            except ValueError as e:
                predicted_cluster = f"Value Conversion Error: {str(e)}"
                session['predicted_cluster'] = predicted_cluster
                flash(f'Please enter valid numeric inputs: {str(e)}', 'danger')
                print("ValueError in K-Means Form:", str(e))
            except Exception as e:
                predicted_cluster = f"Prediction Error: {str(e)}"
                session['predicted_cluster'] = predicted_cluster
                flash(f'Prediction failed: {str(e)}', 'danger')
                print("K-Means prediction exception:", str(e))

        elif form_type == 'arima':
            try:
                if arima_sales_model is None:
                    if arima_load_error:
                        raise Exception(f"ARIMA model failed to load globally: {arima_load_error}")
                    else:
                        raise Exception("ARIMA model is not loaded.")

                # Read forecast months from the form
                months_val = request.form.get('forecast_months')
                forecast_months = int(months_val) if months_val else 12
                session['forecast_months'] = forecast_months

                future_forecast = arima_sales_model.forecast(steps=forecast_months)
                total_forecast = float(sum(future_forecast))
                arima_forecast_val = f"₹{total_forecast:,.2f}"

                historical_sales = pd.Series(arima_sales_model.data.endog, index=arima_sales_model.fittedvalues.index)

                plt.figure(figsize=(10, 5))
                plt.plot(historical_sales.index, historical_sales.values, label='Historical Sales', color='#0d6efd')
                plt.plot(future_forecast.index, future_forecast.values, label=f'{forecast_months}-Month Forecast', color='#dc3545', linestyle='--')
                plt.legend()
                plt.title(f'Sales Forecast for {forecast_months} Month(s)')
                plt.xlabel('Date')
                plt.ylabel('Revenue (₹)')
                plt.grid(True, linestyle='--', alpha=0.5)
                plt.tight_layout()

                charts_dir = os.path.join(current_app.root_path, 'static', 'charts')
                os.makedirs(charts_dir, exist_ok=True)
                chart_path = os.path.join(charts_dir, 'arima_forecast.png')
                plt.savefig(chart_path, dpi=100)
                plt.close()

                session['arima_forecast_active'] = True
                session['arima_forecast_val'] = arima_forecast_val
                session['arima_model_name'] = 'ARIMA(1,1,1)'
                session['arima_rows'] = 1377
                session['arima_years'] = '2020–2023'
                session['arima_points'] = 48
                session['arima_mape'] = '28.16%'
                session['arima_accuracy'] = '71.84%'
                session['arima_error'] = None

                arima_forecast_active = True
                arima_error = None
                arima_chart_exists = True

            except Exception as e:
                arima_error = f"Forecast Failed: {str(e)}"
                session['arima_forecast_active'] = False
                session['arima_error'] = arima_error
                print("ARIMA Forecast exception:", str(e))

    return render_template('ai_insights.html', title='AI Insights', 
                           predicted_sales=predicted_sales, 
                           qty=qty_lin, 
                           price=price_lin, 
                           age=age_lin,
                           predicted_class=predicted_class,
                           qty_log=qty_log,
                           price_log=price_log,
                           age_log=age_log,
                           gender_log=gender_log,
                           category_log=category_log,
                           predicted_cluster=predicted_cluster,
                           spending_kmeans=spending_kmeans,
                           frequency_kmeans=frequency_kmeans,
                           discount_kmeans=discount_kmeans,
                           quantity_kmeans=quantity_kmeans,
                           arima_forecast_active=arima_forecast_active,
                           arima_forecast_val=arima_forecast_val,
                           arima_model_name=arima_model_name,
                           arima_rows=arima_rows,
                           arima_years=arima_years,
                           arima_points=arima_points,
                           arima_mape=arima_mape,
                           arima_accuracy=arima_accuracy,
                           arima_error=arima_error,
                           arima_chart_exists=arima_chart_exists,
                           forecast_months=forecast_months)

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
        
        plt.figure(figsize=(8,5))
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
        
        plt.figure(figsize=(8,5))
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
        
        plt.figure(figsize=(8,5))
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
        
        plt.figure(figsize=(8,5))
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
        
        plt.figure(figsize=(8,5))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, wedgeprops={'edgecolor': 'w'})
        plt.title('Sales by Category', pad=20)
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'product_categories.png'), dpi=100)
        plt.close()
