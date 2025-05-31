# --------------------------- Import Required Libraries ---------------------------
from flask import Flask, render_template, request, redirect, session, abort,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from functools import wraps
import requests
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import pandas as pd

# --------------------------- Flask App Configuration ---------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///admin.db" # SQLite database path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable event system for performance
app.secret_key = "27" # Secret key for managing session securely

# --------------------------- Initialize SQLAlchemy ---------------------------
db = SQLAlchemy(app)

# --------------------------- Database Models ---------------------------

# User table to store login credentials and roles
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, sales, warehouse, production, support

# Product table to store product details
class Product(db.Model):
    __tablename__ = 'product'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

# Request table to track product requests raised by sales users
class Request(db.Model):
    __tablename__ = 'request'
    request_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    request_type = db.Column(db.String(10), nullable=False) # Urgent, Normal
    client_details = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending") # Pending, Fulfilled, In_Production
    request_date = db.Column(db.Date, default=date.today)
    sales_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Used for just convinence purpose 
    product = db.relationship('Product', backref=db.backref('requests', lazy=True))
    sales_user = db.relationship('User', backref=db.backref('sales_requests', lazy=True))

# Inventory table to track stock availability of products
class Inventory(db.Model):
    __tablename__ = 'inventory'
    inventory_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    available_quantity = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.Date, default=date.today, onupdate=date.today)
    # Used for just convinence purpose 
    product = db.relationship('Product', backref=db.backref('inventory', lazy=True))


# Shipment table to log fulfilled requests and shipment details
class Shipment(db.Model):
    shipment_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.request_id'), nullable=False)
    shipped_quantity = db.Column(db.Integer, nullable=False)  
    shipment_date = db.Column(db.Date, nullable=False)
    request = db.relationship("Request", backref=db.backref("shipment",lazy=True))


# Complaint table to track complaints raised by sales users
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sales_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Fulfilled
    created_at = db.Column(db.Date, default=date.today)

    sales_user = db.relationship('User', backref='complaints')


# --------------------------- Create Tables ---------------------------
with app.app_context():
    db.create_all() # Create all tables if they don't exist

# --------------------------- Access Control Decorators ---------------------------

# Require login for accessing specific routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# Restrict access to specific roles or admin
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or (session['role'] != role and session['role'] != 'admin'):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --------------------------- Routes ---------------------------

# --------------------------- Login ---------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        print(username)
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            # Save user info in session
            session['username'] = user.username
            session['user_id'] = user.id
            session['role'] = user.role
            # Redirect based on role
            if user.role == 'sales':
                return redirect("/sales_dashboard")
            elif user.role == 'warehouse':
                return redirect("/warehouse_dashboard")
            elif user.role == 'production':
                return redirect("/production_dashboard")
            elif user.role == 'support':
                return redirect("/support_dashboard")
            else:
                return redirect("/admin_dashboard")
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# Logout and clear session
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# --------------------------- Admin Dashboard ---------------------------
@app.route("/admin_dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")



# --------------------------- Sales ---------------------------


# Sales analytics chart showing number of requests per inventory item
@app.route("/sales_analytics")
@login_required
@role_required("sales")
def sales_analytics():
    # First chart - Inventory Requests
    inv_data = []
    inventories = Inventory.query.all()
    for inv in inventories:
        num_requests = len(inv.product.requests)
        inv_data.append({
            "Product": inv.product.name,
            "Requests": num_requests
        })

    df1 = pd.DataFrame(inv_data)
    plt.figure(figsize=(10, 6))
    df1.set_index("Product")["Requests"].sort_values().plot(kind='barh', color='orange')
    plt.title("Number of Requests per Inventory Product")
    plt.xlabel("Request Count")
    plt.tight_layout()
    img1 = BytesIO()
    plt.savefig(img1, format='png')
    plt.close()
    img1.seek(0)
    chart1_base64 = base64.b64encode(img1.read()).decode('utf-8')

    # Second chart - Inventory Quantities
    qty_data = []
    for inv in inventories:
        qty_data.append({
            "Product": inv.product.name,
            "Quantity": inv.available_quantity
        })

    df2 = pd.DataFrame(qty_data)
    plt.figure(figsize=(10, 6))
    df2.set_index("Product")["Quantity"].sort_values().plot(kind='barh', color='skyblue')
    plt.title("Number of Items in Inventory per Product")
    plt.xlabel("Quantity")
    plt.tight_layout()
    img2 = BytesIO()
    plt.savefig(img2, format='png')
    plt.close()
    img2.seek(0)
    chart2_base64 = base64.b64encode(img2.read()).decode('utf-8')

    return render_template("sales_analytics.html", chart1=chart1_base64, chart2=chart2_base64)


@app.route("/sales_dashboard")
@login_required
@role_required("sales")
def sales_dashboard():
    return render_template("sales_dashboard.html")


# Raise a new sales request
@app.route("/sales_raise_request", methods=["GET", "POST"])
@login_required
@role_required("sales")
def sales_raise_request():
    products = Product.query.all()
    if request.method == "POST":
        new_request = Request(
            product_id=int(request.form["product_id"]),
            quantity=int(request.form["quantity"]),
            request_type=request.form["urgency"],
            client_details=request.form["clientDetails"],
            remarks=request.form["remarks"],
            sales_user_id=session['user_id']  # store user ID
        )
        db.session.add(new_request)
        db.session.commit()
        return redirect("/sales_request_history")
    return render_template("sales_raise_request.html", products=products)

# View request history categorized by status
@app.route("/sales_request_history")
@login_required
@role_required("sales")
def sales_request_history():
    user_requests = Request.query.filter_by(sales_user_id=session['user_id']).all()
    pending_requests = [req for req in user_requests if req.status == "Pending"]
    fulfilled_requests = [req for req in user_requests if req.status == "Fulfilled"]
    production_requests = [req for req in user_requests if req.status == "Production"]
    return render_template("sales_request_history.html",
                           sales_pending_request=pending_requests,
                           sales_fulfilled_request=fulfilled_requests,
                           production_requests=production_requests)


# Raise a complaint by sales user
@app.route("/sales_raise_complaint", methods=["GET", "POST"])
@login_required
@role_required("sales")
def sales_raise_complaint():
    if request.method == "POST":
        subject = request.form["subject"]
        description = request.form["description"]
        complaint = Complaint(
            subject=subject,
            description=description,
            sales_user_id=session["user_id"]
        )
        db.session.add(complaint)
        db.session.commit()
        return redirect("/sales_complaints")
    return render_template("sales_raise_complaint.html")

# View submitted complaints by the logged-in sales user
@app.route("/sales_complaints")
@login_required
@role_required("sales")
def sales_complaints():
    complaints = Complaint.query.filter_by(sales_user_id=session["user_id"]).all()
    return render_template("sales_complaints.html", complaints=complaints)



# --------------------------- Warehouse ---------------------------

# Warehouse dashboard
@app.route("/warehouse_dashboard")
@login_required
@role_required("warehouse")
def warehouse_dashboard():
    return render_template("warehouse_dashboard.html")

# View pending requests and check inventory status
@app.route("/warehouse_pending_requests")
@login_required
@role_required("warehouse")
def warehouse_pending_requests():
    pending_requests = Request.query.filter_by(status="Pending").all()
    production_requests= Request.query.filter_by(status="Production").all()
    inventory_data = Inventory.query.all()
    inventory_map = {inv.product_id: inv.available_quantity for inv in inventory_data}

    request_status_list = []
    for req in pending_requests:
        available_qty = inventory_map.get(req.product_id, 0)
        if available_qty >= req.quantity:
            status = "ReadyToShip"
        elif available_qty > 0:
            status = "PartialStock"
        else:
            status = "OutOfStock"
        request_status_list.append({
            "request": req,
            "available_quantity": available_qty,
            "status": status
        })
    return render_template("warehouse_pending_requests.html", request_status_list=request_status_list,
                           production_requests=production_requests)


# Process a shipment when inventory is available
@app.route("/process_shipment/<int:request_id>", methods=["POST"])
@login_required
@role_required("warehouse")
def process_shipment(request_id):
    req = Request.query.get(request_id)

    # Only proceed if the request is still pending
    if req.status != "Pending":
        return redirect(url_for("warehouse_pending_requests", msg="Invalid status"))

    # Fetch inventory
    inventory = Inventory.query.filter_by(product_id=req.product_id).first()
    if not inventory or inventory.available_quantity < req.quantity:
        return redirect(url_for("warehouse_pending_requests", msg="Not enough stock"))

    # Reduce inventory
    inventory.available_quantity -= req.quantity

    # Create shipment record
    shipment = Shipment(
        request_id=req.request_id,
        shipment_date=date.today(),
        shipped_quantity=req.quantity
    )
    db.session.add(shipment)

    # Update request status
    req.status = "Fulfilled"
    db.session.commit()

    return redirect(url_for("warehouse_pending_requests", msg="Shipped Successfully"))

# Request production
@app.route("/request_production", methods=["POST"])
@login_required
@role_required("warehouse")
def request_production():
    request_id = int(request.form.get("request_id"))

    # Fetch the request object
    req = Request.query.get(request_id)

    if not req:
        return redirect(url_for("warehouse_pending_requests", msg="Request not found"))

    # Check if already in production or beyond
    if req.status == "Production":
        return redirect(url_for("warehouse_pending_requests", msg="Already in production"))

    # Update status to In Production
    req.status = "Production"
    db.session.commit()

    return redirect(url_for("warehouse_pending_requests", msg="Successfully requested to Production"))


@app.route("/warehouse_live_inventory")
@login_required
@role_required("warehouse")
def warehouse_live_inventory():
    inventory = Inventory.query.all()
    return render_template("warehouse_live_inventory.html", inventory=inventory)

@app.route("/warehouse_threshold_alerts")
@login_required
@role_required("warehouse")
def warehouse_threshold_alerts():
    all_inventory = Inventory.query.all()
    alerts = [item for item in all_inventory if item.available_quantity <= 10]
    return render_template("warehouse_threshold_alerts.html", alerts=alerts)

@app.route("/warehouse_shipment_log")
@login_required
@role_required("warehouse")
def warehouse_shipment_log():
    shipments = Shipment.query.all()
    return render_template("warehouse_shipment_log.html", shipments=shipments)

# --------------------------- Production ---------------------------
@app.route("/production_dashboard")
@login_required
@role_required("production")
def production_dashboard():
    return render_template("production_dashboard.html")


# Production pending requests
@app.route("/production_pending_requests")
@login_required
@role_required("production")
def production_pending_requests():
    # Fetch all requests with status "Production"
    production_requests = Request.query.filter_by(status="Production").all()

    # Render the template with both production requests and inventory map
    return render_template(
        "production_pending_requests.html",
        production_requests=production_requests,
    )

@app.route("/refill_inventory/<int:request_id>", methods=["POST"])
@login_required
@role_required("production")
def refill_inventory(request_id):
    request_obj = Request.query.get(request_id)
    inventory = Inventory.query.filter_by(product_id=request_obj.product_id).first()

    if not inventory:
        return redirect(url_for("production_pending_requests", msg="❌ Inventory entry not found for this product."))
    
    # Add required quantity (if any)
    inventory.available_quantity += request_obj.quantity
    inventory.last_updated = date.today()
    # Mark the request as pending
    request_obj.status = "Pending"

    db.session.commit()

    return redirect(url_for("production_pending_requests", msg="✅ Inventory refilled successfully."))


@app.route("/production_live_inventory")
@login_required
@role_required("production")
def production_live_inventory():
    inventory = Inventory.query.all()
    return render_template("production_live_inventory.html", inventory=inventory)

@app.route("/production_threshold_alerts")
@login_required
@role_required("production")
def production_threshold_alerts():
    all_inventory = Inventory.query.all()
    alerts = [item for item in all_inventory if item.available_quantity <= 10]
    return render_template("production_threshold_alerts.html", alerts=alerts)

# --------------------------- Support ---------------------------
@app.route("/support_dashboard")
@login_required
@role_required("support")
def support_dashboard():
    return render_template("support_dashboard.html")

# --- Support View All Complaints ---
@app.route("/support_complaints")
@login_required
@role_required("support")
def support_complaints():
    complaints = Complaint.query.all()
    return render_template("support_complaints.html", complaints=complaints)


@app.route("/support/respond/<int:complaint_id>")
@login_required
@role_required("support")
def respond_complaint(complaint_id):
    # Fetch the complaint, mark it as resolved or handle accordingly
    complaint = Complaint.query.get(complaint_id)
    if complaint.status == "Pending":
        complaint.status = "Resolved"
        db.session.commit()
    return redirect(url_for('support_complaints'))  # or wherever you list them


# --------------------------- Industry Alerts ---------------------------
@app.route("/industry_alerts")
@login_required
def industry_alerts():
    url = 'https://newsapi.org/v2/everything?q=sports&apiKey=03a10f6261204e4da4a462904109d95e'
    response = requests.get(url)
    data = response.json()
    articles = data.get("articles", [])[:10] if data.get("status") == "ok" else []
    return render_template("industry_alerts.html", articles=articles)


# --------------------------- Prevent Browser Caching After Logout ---------------------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# --------------------------- Run App ---------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
