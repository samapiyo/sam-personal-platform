
from decimal import Decimal

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user

from ..extensions import db
from ..mpesa import initiate_stk_push, normalize_phone
from ..models import Product, Order, OrderItem, Activity, MpesaPayment


business_bp = Blueprint(
    "business",
    __name__,
    url_prefix="/business",
)


def _cart():
    return session.get("cart", {})


def _save_cart(cart):
    session["cart"] = cart
    session.modified = True


def _cart_products():
    cart = _cart()

    if not cart:
        return [], Decimal("0.00")

    ids = []

    for key in cart:
        try:
            ids.append(int(key))
        except ValueError:
            continue

    products = (
        Product.query
        .filter(
            Product.id.in_(ids),
            Product.is_active.is_(True),
        )
        .all()
        if ids
        else []
    )

    by_id = {
        str(product.id): product
        for product in products
    }

    items = []
    total = Decimal("0.00")
    cleaned = {}

    for key, quantity in cart.items():
        product = by_id.get(str(key))

        if not product or product.stock <= 0:
            continue

        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            continue

        quantity = min(quantity, product.stock)

        cleaned[str(product.id)] = quantity

        subtotal = (
            Decimal(str(product.price))
            * quantity
        )

        total += subtotal

        items.append(
            {
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )

    if cleaned != cart:
        _save_cart(cleaned)

    return items, total


def record(action):
    db.session.add(
        Activity(
            user_id=(
                current_user.id
                if current_user.is_authenticated
                else None
            ),
            action=action,
            path=request.path,
            ip_address=request.remote_addr,
            user_agent=request.headers.get(
                "User-Agent",
                "",
            )[:500],
        )
    )

    db.session.commit()


@business_bp.route("/")
def index():
    products = (
        Product.query
        .filter_by(is_active=True)
        .order_by(Product.created_at.desc())
        .all()
    )

    categories = [
        row[0]
        for row in (
            db.session
            .query(Product.category)
            .filter(Product.is_active.is_(True))
            .distinct()
            .order_by(Product.category)
            .all()
        )
        if row[0]
    ]

    selected_category = (
        request.args.get("category", "").strip()
    )

    if selected_category:
        products = [
            product
            for product in products
            if product.category == selected_category
        ]

    return render_template(
        "business/index.html",
        products=products,
        categories=categories,
        selected_category=selected_category,
    )


@business_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = (
        Product.query
        .filter_by(
            id=product_id,
            is_active=True,
        )
        .first_or_404()
    )

    return render_template(
        "business/product.html",
        product=product,
    )


@business_bp.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    product = (
        Product.query
        .filter_by(
            id=product_id,
            is_active=True,
        )
        .first_or_404()
    )

    if product.stock < 1:
        flash(
            "This product is currently out of stock.",
            "error",
        )

        return redirect(
            request.referrer
            or url_for("business.index")
        )

    try:
        quantity = max(
            1,
            int(request.form.get("quantity", "1")),
        )
    except ValueError:
        quantity = 1

    cart = _cart()

    current = int(
        cart.get(str(product.id), 0)
    )

    cart[str(product.id)] = min(
        current + quantity,
        product.stock,
    )

    _save_cart(cart)

    flash(
        f"{product.name} added to your cart.",
        "success",
    )

    return redirect(
        request.referrer
        or url_for("business.index")
    )


@business_bp.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        cart_data = {}

        for key, value in request.form.items():
            if not key.startswith("qty_"):
                continue

            product_id = key[4:]

            try:
                quantity = int(value)
            except ValueError:
                quantity = 0

            if quantity > 0:
                product = (
                    Product.query
                    .filter_by(
                        id=int(product_id),
                        is_active=True,
                    )
                    .first()
                )

                if product:
                    cart_data[product_id] = min(
                        quantity,
                        product.stock,
                    )

        _save_cart(cart_data)

        flash(
            "Cart updated.",
            "success",
        )

        return redirect(
            url_for("business.cart")
        )

    items, total = _cart_products()

    return render_template(
        "business/cart.html",
        items=items,
        total=total,
    )


@business_bp.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = _cart()

    cart.pop(
        str(product_id),
        None,
    )

    _save_cart(cart)

    flash(
        "Item removed from cart.",
        "success",
    )

    return redirect(
        url_for("business.cart")
    )


@business_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = _cart_products()

    if not items:
        flash(
            "Your cart is empty.",
            "error",
        )

        return redirect(
            url_for("business.index")
        )

    if request.method == "POST":

        # Re-check stock immediately before creating the order.
        for item in items:
            product = db.session.get(
                Product,
                item["product"].id,
            )

            if (
                not product
                or not product.is_active
                or product.stock < item["quantity"]
            ):
                flash(
                    f"Stock changed for "
                    f"{item['product'].name}. "
                    "Please review your cart.",
                    "error",
                )

                return redirect(
                    url_for("business.cart")
                )

        order = Order(
            user_id=current_user.id,
            total=total,
            payment_status="unpaid",
            order_status="pending",
        )

        db.session.add(order)
        db.session.flush()

        for item in items:
            product = db.session.get(
                Product,
                item["product"].id,
            )

            product.stock -= item["quantity"]

            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item["quantity"],
                    price=product.price,
                )
            )

        db.session.add(
            Activity(
                user_id=current_user.id,
                action=f"Created order #{order.id}",
                path=request.path,
                ip_address=request.remote_addr,
                user_agent=request.headers.get(
                    "User-Agent",
                    "",
                )[:500],
            )
        )

        db.session.commit()

        _save_cart({})

        return redirect(
            url_for(
                "business.pay_order",
                order_id=order.id,
            )
        )

    return render_template(
        "business/checkout.html",
        items=items,
        total=total,
    )


@business_bp.route(
    "/pay/<int:order_id>",
    methods=["GET", "POST"],
)
@login_required
def pay_order(order_id):
    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id,
        )
        .first_or_404()
    )

    if order.payment_status == "paid":
        flash(
            "This order has already been paid.",
            "success",
        )

        return redirect(
            url_for(
                "business.order_confirmation",
                order_id=order.id,
            )
        )

    payment = (
        MpesaPayment.query
        .filter_by(order_id=order.id)
        .first()
    )

    if request.method == "POST":
        phone = request.form.get(
            "phone",
            "",
        ).strip()

        try:
            normalized = normalize_phone(phone)

        except ValueError as exc:
            flash(
                str(exc),
                "error",
            )

            return render_template(
                "business/pay.html",
                order=order,
                payment=payment,
            )

        callback_url = current_app.config.get(
            "MPESA_CALLBACK_URL",
            "",
        ).strip()

        if not callback_url:
            flash(
                "M-Pesa is not configured yet. "
                "Set MPESA_CALLBACK_URL in your environment.",
                "error",
            )

            return render_template(
                "business/pay.html",
                order=order,
                payment=payment,
            )

        try:
            data, normalized = initiate_stk_push(
                order.id,
                order.total,
                normalized,
                callback_url,
            )

            if data.get("ResponseCode") != "0":
                raise RuntimeError(
                    data.get("ResponseDescription")
                    or "Daraja rejected the STK Push request."
                )

            if payment is None:
                payment = MpesaPayment(
                    order_id=order.id,
                    phone_number=normalized,
                    amount=order.total,
                )

                db.session.add(payment)

            payment.phone_number = normalized
            payment.amount = order.total
            payment.status = "pending"

            payment.merchant_request_id = (
                data.get("MerchantRequestID")
            )

            payment.checkout_request_id = (
                data.get("CheckoutRequestID")
            )

            payment.result_code = None

            payment.result_description = (
                data.get("CustomerMessage")
                or data.get("ResponseDescription")
            )

            order.payment_status = "pending"

            db.session.commit()

            # PRG pattern:
            # Redirect to a GET page instead of rendering
            # the pending page directly from this POST request.
            return redirect(
                url_for(
                    "business.payment_pending",
                    order_id=order.id,
                )
            )

        except Exception as exc:
            db.session.rollback()

            current_app.logger.exception(
                "M-Pesa STK Push failed"
            )

            flash(
                f"Could not start M-Pesa payment: {exc}",
                "error",
            )

            return render_template(
                "business/pay.html",
                order=order,
                payment=payment,
            )

    return render_template(
        "business/pay.html",
        order=order,
        payment=payment,
    )


@business_bp.route(
    "/payment-pending/<int:order_id>"
)
@login_required
def payment_pending(order_id):
    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id,
        )
        .first_or_404()
    )

    payment = (
        MpesaPayment.query
        .filter_by(order_id=order.id)
        .first()
    )

    if order.payment_status == "paid":
        return redirect(
            url_for(
                "business.order_confirmation",
                order_id=order.id,
            )
        )

    return render_template(
        "business/payment_pending.html",
        order=order,
        payment=payment,
    )


@business_bp.route("/payment-status/<int:order_id>", methods=["GET"])
@login_required
def payment_status(order_id):
    order = Order.query.get_or_404(order_id)

    # Only allow the owner of the order to check its payment status.
    if order.user_id != current_user.id:
        abort(403)

    payment = (
        MpesaPayment.query
        .filter_by(order_id=order.id)
        .order_by(MpesaPayment.id.desc())
        .first()
    )

    if payment is None:
        return jsonify(
            {
                "order_id": order.id,
                "payment_status": order.payment_status or "unpaid",
                "payment_status_detail": None,
                "result_code": None,
                "result_description": None,
                "paid": False,
                "cancelled": False,
                "failed": False,
                "pending": False,
            }
        )

    status = (payment.status or "").lower()

    return jsonify(
        {
            # Current API fields
            "order_id": order.id,
            "payment_status": order.payment_status or "unpaid",
            "payment_status_detail": status,
            "result_code": payment.result_code,
            "result_description": payment.result_description,

            # Boolean compatibility fields
            "paid": (
                order.payment_status == "paid"
                or status == "paid"
            ),
            "cancelled": (
                status == "cancelled"
            ),
            "failed": (
                status == "failed"
            ),
            "pending": (
                status == "pending"
                and order.payment_status != "paid"
            ),

            # Useful compatibility aliases
            "status": status,
            "message": (
                payment.result_description
                or status
                or order.payment_status
                or "Payment status unavailable."
            ),
        }
    )


@business_bp.post("/payment/callback")
def mpesa_callback():
    payload = request.get_json(
        silent=True
    ) or {}

    current_app.logger.warning(
    "M-PESA CALLBACK RECEIVED: %s",
    payload,
)

    callback = (
        payload
        .get("Body", {})
        .get("stkCallback", {})
    )

    checkout_request_id = (
        callback.get("CheckoutRequestID")
    )

    result_code = callback.get(
        "ResultCode"
    )

    result_description = callback.get(
        "ResultDesc",
        "",
    )

    if not checkout_request_id:
        return jsonify(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            }
        )

    payment = (
        MpesaPayment.query
        .filter_by(
            checkout_request_id=checkout_request_id
        )
        .first()
    )

    if not payment:
        current_app.logger.warning(
            "Unknown M-Pesa CheckoutRequestID: %s",
            checkout_request_id,
        )

        return jsonify(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            }
        )

    payment.result_code = (
        str(result_code)
        if result_code is not None
        else None
    )

    payment.result_description = result_description

    # ResultCode 0 = successful payment.
    if str(result_code) == "0":

        metadata = (
            callback
            .get("CallbackMetadata", {})
            .get("Item", [])
        )

        values = {
            item.get("Name"): item.get("Value")
            for item in metadata
            if item.get("Name")
        }

        payment.status = "paid"

        payment.mpesa_receipt = (
            str(values.get("MpesaReceiptNumber"))
            if values.get("MpesaReceiptNumber") is not None
            else None
        )

        payment.transaction_date = (
            str(values.get("TransactionDate"))
            if values.get("TransactionDate") is not None
            else None
        )

        payment.amount = (
            values.get("Amount")
            or payment.amount
        )

        payment.order.payment_status = "paid"
        payment.order.order_status = "processing"

    # ResultCode 1032 = customer cancelled the STK prompt.
    elif str(result_code) == "1032":

        payment.status = "cancelled"

        payment.order.payment_status = "failed"

    # Any other non-zero result is treated as a payment failure.
    else:

        payment.status = "failed"

        payment.order.payment_status = "failed"

    db.session.commit()

    return jsonify(
        {
            "ResultCode": 0,
            "ResultDesc": "Accepted",
        }
    )


@business_bp.route("/orders")
@login_required
def orders():
    orders = (
        Order.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return render_template(
        "business/my_orders.html",
        orders=orders,
    )


@business_bp.route(
    "/orders/<int:order_id>"
)
@login_required
def order_confirmation(order_id):
    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id,
        )
        .first_or_404()
    )

    return render_template(
        "business/order_confirmation.html",
        order=order,
    )

