from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
import os
import uuid

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    Activity,
    User,
    BlogPost,
    Product,
    Order,
    SupportTicket,
    SupportReply,
    Opportunity,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# =========================================
# ADMIN ACCESS
# =========================================

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("Administrator access required.", "error")
            return redirect(url_for("main.home"))

        return view(*args, **kwargs)

    return wrapped


# =========================================
# PRODUCT IMAGE UPLOAD SETTINGS
# =========================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
}


def allowed_image(filename):
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


def save_product_image(image):
    """
    Save an uploaded product image inside:
    app/static/uploads/products/
    """

    if not image or not image.filename:
        return ""

    if not allowed_image(image.filename):
        return None

    filename = secure_filename(image.filename)

    # Add a unique prefix so two products can use files
    # with the same original filename.
    extension = filename.rsplit(".", 1)[1].lower()

    unique_filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "products",
    )

    os.makedirs(
        upload_folder,
        exist_ok=True,
    )

    image.save(
        os.path.join(
            upload_folder,
            unique_filename,
        )
    )

    return url_for(
        "static",
        filename=f"uploads/products/{unique_filename}",
    )


# =========================================
# DASHBOARD
# =========================================

@admin_bp.route("/")
@admin_required
def dashboard():

    stats = {
        "users": User.query.count(),
        "pending_blogs": BlogPost.query.filter_by(
            status="pending"
        ).count(),
        "products": Product.query.filter_by(
            is_active=True
        ).count(),
        "orders": Order.query.count(),
        "open_support": SupportTicket.query.filter_by(
            status="open"
        ).count(),
        "opportunities": Opportunity.query.filter_by(
            published=True
        ).count(),
    }

    activities = (
        Activity.query
        .order_by(Activity.created_at.desc())
        .limit(25)
        .all()
    )

    pending_blogs = (
        BlogPost.query
        .filter_by(status="pending")
        .order_by(BlogPost.created_at.desc())
        .limit(8)
        .all()
    )

    recent_orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        activities=activities,
        pending_blogs=pending_blogs,
        recent_orders=recent_orders,
    )


# =========================================
# USERS
# =========================================

@admin_bp.route("/users")
@admin_required
def users():

    users = (
        User.query
        .order_by(User.id.desc())
        .all()
    )

    return render_template(
        "admin/users.html",
        users=users,
    )


@admin_bp.route(
    "/users/<int:user_id>/edit",
    methods=["GET", "POST"],
)
@admin_required
def edit_user(user_id):

    user = db.get_or_404(
        User,
        user_id,
    )

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        if not username or not email:

            flash(
                "Username and email are required.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_user",
                    user_id=user.id,
                )
            )

        existing_username = (
            User.query
            .filter(
                User.username == username,
                User.id != user.id,
            )
            .first()
        )

        if existing_username:

            flash(
                "That username is already in use.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_user",
                    user_id=user.id,
                )
            )

        existing_email = (
            User.query
            .filter(
                User.email == email,
                User.id != user.id,
            )
            .first()
        )

        if existing_email:

            flash(
                "That email address is already in use.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_user",
                    user_id=user.id,
                )
            )

        user.username = username
        user.email = email

        db.session.commit()

        flash(
            "User updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin.users")
        )

    return render_template(
        "admin/edit_user.html",
        user=user,
    )


@admin_bp.route(
    "/users/<int:user_id>/toggle-admin",
    methods=["POST"],
)
@admin_required
def toggle_admin(user_id):

    user = db.get_or_404(
        User,
        user_id,
    )

    if user.id == current_user.id:

        flash(
            "You cannot remove your own administrator access here.",
            "error",
        )

    else:

        user.is_admin = not user.is_admin

        db.session.commit()

        flash(
            f"Administrator status updated for {user.username}.",
            "success",
        )

    return redirect(
        url_for("admin.users")
    )


@admin_bp.route(
    "/users/<int:user_id>/toggle-active",
    methods=["POST"],
)
@admin_required
def toggle_user_active(user_id):

    user = db.get_or_404(
        User,
        user_id,
    )

    if user.id == current_user.id:

        flash(
            "You cannot disable your own account.",
            "error",
        )

    else:

        user.is_active = not user.is_active

        db.session.commit()

        status = (
            "enabled"
            if user.is_active
            else "disabled"
        )

        flash(
            f"User {user.username} has been {status}.",
            "success",
        )

    return redirect(
        url_for("admin.users")
    )


# =========================================
# BLOG
# =========================================

@admin_bp.route("/blog")
@admin_required
def blog():

    posts = (
        BlogPost.query
        .order_by(BlogPost.created_at.desc())
        .all()
    )

    return render_template(
        "admin/blog.html",
        posts=posts,
    )


@admin_bp.route(
    "/blog/<int:post_id>/edit",
    methods=["GET", "POST"],
)
@admin_required
def edit_blog(post_id):

    post = db.get_or_404(
        BlogPost,
        post_id,
    )

    if request.method == "POST":

        title = request.form.get(
            "title",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "General",
        ).strip() or "General"

        content = request.form.get(
            "content",
            "",
        ).strip()

        if not title or not content:

            flash(
                "Title and content are required.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_blog",
                    post_id=post.id,
                )
            )

        post.title = title
        post.category = category
        post.content = content

        db.session.commit()

        flash(
            "Blog post updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin.blog")
        )

    return render_template(
        "admin/edit_blog.html",
        post=post,
    )


@admin_bp.route(
    "/blog/<int:post_id>/<action>",
    methods=["POST"],
)
@admin_required
def moderate_blog(post_id, action):

    post = db.get_or_404(
        BlogPost,
        post_id,
    )

    if action not in {
        "approve",
        "reject",
    }:

        flash(
            "Unknown moderation action.",
            "error",
        )

        return redirect(
            url_for("admin.blog")
        )

    post.status = (
        "approved"
        if action == "approve"
        else "rejected"
    )

    post.reviewed_at = datetime.now(
        timezone.utc
    )

    db.session.commit()

    flash(
        f"Blog post {post.status}.",
        "success",
    )

    return redirect(
        url_for("admin.blog")
    )


@admin_bp.route(
    "/blog/<int:post_id>/delete",
    methods=["POST"],
)
@admin_required
def delete_blog(post_id):

    post = db.get_or_404(
        BlogPost,
        post_id,
    )

    db.session.delete(post)

    db.session.commit()

    flash(
        "Blog post deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.blog")
    )


# =========================================
# PRODUCTS
# =========================================

@admin_bp.route(
    "/products",
    methods=["GET", "POST"],
)
@admin_required
def products():

    if request.method == "POST":

        name = request.form.get(
            "name",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "General",
        ).strip() or "General"

        # ---------------------------------
        # IMAGE UPLOAD
        # ---------------------------------

        image = request.files.get(
            "image"
        )

        image_url = ""

        if image and image.filename:

            image_url = save_product_image(
                image
            )

            if image_url is None:

                flash(
                    "Invalid image type. Use JPG, JPEG, PNG, GIF or WEBP.",
                    "error",
                )

                return redirect(
                    url_for("admin.products")
                )

        # ---------------------------------
        # PRICE AND STOCK
        # ---------------------------------

        try:

            price = Decimal(
                request.form.get(
                    "price",
                    "0",
                )
            )

            stock = int(
                request.form.get(
                    "stock",
                    "0",
                )
            )

        except (
            InvalidOperation,
            ValueError,
        ):

            flash(
                "Price and stock must contain valid numbers.",
                "error",
            )

            return redirect(
                url_for("admin.products")
            )

        # ---------------------------------
        # VALIDATE PRODUCT
        # ---------------------------------

        if (
            not name
            or price < 0
            or stock < 0
        ):

            flash(
                "Enter a product name and valid non-negative price/stock.",
                "error",
            )

            return redirect(
                url_for("admin.products")
            )

        # ---------------------------------
        # CREATE PRODUCT
        # ---------------------------------

        product = Product(
            name=name,
            description=description,
            category=category,
            image_url=image_url,
            price=price,
            stock=stock,
        )

        db.session.add(
            product
        )

        db.session.commit()

        flash(
            "Product created successfully.",
            "success",
        )

        return redirect(
            url_for("admin.products")
        )

    # ---------------------------------
    # DISPLAY PRODUCTS
    # ---------------------------------

    products = (
        Product.query
        .order_by(Product.created_at.desc())
        .all()
    )

    return render_template(
        "admin/products.html",
        products=products,
    )

@admin_bp.route(
    "/products/<int:product_id>/edit",
    methods=["GET", "POST"],
)
@admin_required
def edit_product(product_id):

    product = db.get_or_404(
        Product,
        product_id,
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "General",
        ).strip() or "General"

        try:

            price = Decimal(
                request.form.get(
                    "price",
                    "0",
                )
            )

            stock = int(
                request.form.get(
                    "stock",
                    "0",
                )
            )

        except (
            InvalidOperation,
            ValueError,
        ):

            flash(
                "Price and stock must contain valid numbers.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_product",
                    product_id=product.id,
                )
            )

        if (
            not name
            or price < 0
            or stock < 0
        ):

            flash(
                "Enter a product name and valid non-negative price/stock.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_product",
                    product_id=product.id,
                )
            )

        product.name = name
        product.description = description
        product.category = category
        product.price = price
        product.stock = stock

        db.session.commit()

        flash(
            "Product updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin.products")
        )

    return render_template(
        "admin/edit_product.html",
        product=product,
    )


@admin_bp.route(
    "/products/<int:product_id>/toggle",
    methods=["POST"],
)
@admin_required
def toggle_product(product_id):

    product = db.get_or_404(
        Product,
        product_id,
    )

    product.is_active = not product.is_active

    db.session.commit()

    flash(
        "Product visibility updated.",
        "success",
    )

    return redirect(
        url_for("admin.products")
    )

@admin_bp.route(
    "/products/<int:product_id>/delete",
    methods=["POST"],
)
@admin_required
def delete_product(product_id):

    product = db.get_or_404(
        Product,
        product_id,
    )

    db.session.delete(product)
    db.session.commit()

    flash(
        "Product deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.products")
    )


# =========================================
# ORDERS
# =========================================

@admin_bp.route("/orders")
@admin_required
def orders():

    orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template(
        "admin/orders.html",
        orders=orders,
    )


@admin_bp.route(
    "/orders/<int:order_id>",
)
@admin_required
def order_details(order_id):

    order = db.get_or_404(
        Order,
        order_id,
    )

    return render_template(
        "admin/order_details.html",
        order=order,
    )


@admin_bp.route(
    "/orders/<int:order_id>/status",
    methods=["POST"],
)
@admin_required
def order_status(order_id):

    order = db.get_or_404(
        Order,
        order_id,
    )

    status = request.form.get(
        "order_status",
        "pending",
    ).strip().lower()

    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "cancelled",
    }

    if status not in allowed_statuses:

        flash(
            "Invalid order status.",
            "error",
        )

        return redirect(
            url_for("admin.orders")
        )

    order.order_status = status

    db.session.commit()

    flash(
        "Order status updated successfully.",
        "success",
    )

    return redirect(
        url_for("admin.orders")
    )


# =========================================
# SUPPORT
# =========================================

@admin_bp.route("/support")
@admin_required
def support():

    return render_template(
        "admin/support.html",
        tickets=SupportTicket.query
        .order_by(SupportTicket.created_at.desc())
        .all(),
    )


@admin_bp.route(
    "/support/<int:ticket_id>"
)
@admin_required
def support_ticket(ticket_id):

    ticket = db.get_or_404(
        SupportTicket,
        ticket_id,
    )

    replies = (
        SupportReply.query
        .filter_by(
            ticket_id=ticket.id
        )
        .order_by(
            SupportReply.created_at.asc()
        )
        .all()
    )

    return render_template(
        "admin/support_ticket.html",
        ticket=ticket,
        replies=replies,
    )

@admin_bp.route(
    "/support/<int:ticket_id>/reply",
    methods=["POST"],
)
@admin_required
def support_reply(ticket_id):

    ticket = db.get_or_404(
        SupportTicket,
        ticket_id,
    )

    message = request.form.get(
        "message",
        "",
    ).strip()

    if not message:
        flash(
            "Reply message cannot be empty.",
            "error",
        )

        return redirect(
            url_for(
                "admin.support_ticket",
                ticket_id=ticket.id,
            )
        )

    reply = SupportReply(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=message,
        is_admin=True,
    )

    db.session.add(reply)

    ticket.status = "in_progress"

    activity = Activity(
        user_id=current_user.id,
        action="support_reply_sent",
        path=f"/admin/support/{ticket.id}",
    )

    db.session.add(activity)

    db.session.commit()

    flash(
        "Reply sent successfully.",
        "success",
    )

    return redirect(
        url_for(
            "admin.support_ticket",
            ticket_id=ticket.id,
        )
    )


@admin_bp.route(
    "/support/<int:ticket_id>/status",
    methods=["POST"],
)
@admin_required
def support_status(ticket_id):

    ticket = db.get_or_404(
        SupportTicket,
        ticket_id,
    )

    old_status = ticket.status

    status = request.form.get(
        "status",
        "open",
    )

    allowed_statuses = {
        "open",
        "in_progress",
        "resolved",
        "closed",
    }

    if status not in allowed_statuses:

        flash(
            "Invalid support status.",
            "error",
        )

        return redirect(
            url_for(
                "admin.support_ticket",
                ticket_id=ticket.id,
            )
        )

    ticket.status = status

    if old_status != status:

        activity = Activity(
            user_id=current_user.id,
            action="support_status_changed",
            path=f"/admin/support/{ticket.id}",
        )

        db.session.add(
            activity
        )

    db.session.commit()

    flash(
        "Support ticket updated.",
        "success",
    )

    return redirect(
        url_for(
            "admin.support_ticket",
            ticket_id=ticket.id,
        )
    )




# =========================================
# OPPORTUNITIES
# =========================================

@admin_bp.route("/opportunities")
@admin_required
def opportunities():

    return render_template(
        "admin/opportunities.html",
        opportunities=Opportunity.query
        .order_by(Opportunity.created_at.desc())
        .all(),
    )


@admin_bp.route(
    "/opportunities/new",
    methods=["POST"],
)
@admin_required
def create_opportunity():

    title = request.form.get(
        "title",
        "",
    ).strip()

    description = request.form.get(
        "description",
        "",
    ).strip()

    category = request.form.get(
        "category",
        "General",
    ).strip() or "General"

    application_url = request.form.get(
        "application_url",
        "",
    ).strip()

    if not title or not description:

        flash(
            "Title and description are required.",
            "error",
        )

        return redirect(
            url_for("admin.opportunities")
        )

    opportunity = Opportunity(
        title=title,
        description=description,
        category=category,
        application_url=application_url,
        published=(
            request.form.get(
                "published"
            ) == "on"
        ),
    )

    db.session.add(opportunity)
    db.session.commit()

    flash(
        "Opportunity created.",
        "success",
    )

    return redirect(
        url_for("admin.opportunities")
    )


@admin_bp.route(
    "/opportunities/<int:opportunity_id>/edit",
    methods=["GET", "POST"],
)
@admin_required
def edit_opportunity(opportunity_id):

    opportunity = db.get_or_404(
        Opportunity,
        opportunity_id,
    )

    if request.method == "POST":

        title = request.form.get(
            "title",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "General",
        ).strip() or "General"

        application_url = request.form.get(
            "application_url",
            "",
        ).strip()

        if not title or not description:

            flash(
                "Title and description are required.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.edit_opportunity",
                    opportunity_id=opportunity.id,
                )
            )

        opportunity.title = title
        opportunity.description = description
        opportunity.category = category
        opportunity.application_url = application_url

        db.session.commit()

        flash(
            "Opportunity updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin.opportunities")
        )

    return render_template(
        "admin/edit_opportunity.html",
        opportunity=opportunity,
    )


@admin_bp.route(
    "/opportunities/<int:opportunity_id>/toggle",
    methods=["POST"],
)
@admin_required
def toggle_opportunity(opportunity_id):

    opportunity = db.get_or_404(
        Opportunity,
        opportunity_id,
    )

    opportunity.published = not opportunity.published

    db.session.commit()

    flash(
        "Opportunity publication status updated.",
        "success",
    )

    return redirect(
        url_for("admin.opportunities")
    )


@admin_bp.route(
    "/opportunities/<int:opportunity_id>/delete",
    methods=["POST"],
)
@admin_required
def delete_opportunity(opportunity_id):

    opportunity = db.get_or_404(
        Opportunity,
        opportunity_id,
    )

    db.session.delete(opportunity)
    db.session.commit()

    flash(
        "Opportunity deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.opportunities")
    )


# =========================================
# ACTIVITY
# =========================================

@admin_bp.route("/activity")
@admin_required
def activity():

    activities = (
        Activity.query
        .order_by(Activity.created_at.desc())
        .limit(250)
        .all()
    )

    return render_template(
        "admin/activity.html",
        activities=activities,
    )