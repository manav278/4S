# 4S Inventory & Workflow Management System

A Flask-based web application for managing inventory, product requests, shipments, complaints, and analytics for a multi-role organization.  
Roles supported: **Admin, Sales, Warehouse, Production, Support**.

---

## Features

### Authentication & Authorization
- Secure login/logout for all users.
- Role-based access control (Admin, Sales, Warehouse, Production, Support).

### Admin
- Dashboard for admin overview.
- Register new users with roles.

### Sales
- Dashboard for sales users.
- Raise new product requests (with urgency, client details, remarks).
- View request history (Pending, Fulfilled, Production).
- Raise and view complaints.
- View sales analytics (requests per product, inventory levels).

### Warehouse
- Dashboard for warehouse staff.
- View and process pending product requests.
- Check inventory status and shipment readiness.
- Mark requests as shipped and update inventory.
- Request production for out-of-stock items.
- View live inventory and threshold alerts.
- View shipment logs.

### Production
- Dashboard for production planners.
- View and manage production pending requests.
- **Increase inventory quantity directly from the live inventory page.**
- Mark production requests as refilled (moves request back to pending).
- View threshold alerts for low stock.

### Support
- Dashboard for support staff.
- View and resolve all complaints.

### Industry Alerts
- View latest industry news (example: sports news via NewsAPI).

---

## Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Frontend:** HTML, Bootstrap 5, Jinja2 templates
- **Database:** SQLite (admin.db)
- **Visualization:** Matplotlib, Pandas

---