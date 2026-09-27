from datetime import datetime, timezone
from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    excerpt = db.Column(db.String(500), default="")
    category = db.Column(db.String(100), default="General", nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending/approved/rejected
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship("User", backref=db.backref("blog_posts", lazy=True))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    image_url = db.Column(db.String(500), default="")
    category = db.Column(db.String(100), default="General")
    stock = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    payment_status = db.Column(db.String(30), default="unpaid", nullable=False)
    order_status = db.Column(db.String(30), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    product = db.relationship("Product")


class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="open", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("support_tickets", lazy=True))


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default="General")
    description = db.Column(db.Text, nullable=False)
    application_url = db.Column(db.String(500), default="")
    published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class MpesaPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False, unique=True)
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), default="initiated", nullable=False)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    checkout_request_id = db.Column(db.String(100), nullable=True, index=True)
    mpesa_receipt = db.Column(db.String(100), nullable=True)
    result_code = db.Column(db.String(20), nullable=True)
    result_description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    order = db.relationship("Order", backref=db.backref("mpesa_payment", uselist=False))
class SupportReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("support_ticket.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    message = db.Column(db.Text, nullable=False)

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=utcnow,
        nullable=False
    )

    ticket = db.relationship(
        "SupportTicket",
        backref=db.backref(
            "replies",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    user = db.relationship("User")