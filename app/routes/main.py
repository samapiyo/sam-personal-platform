from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Activity, SupportReply, SupportTicket


main_bp = Blueprint("main", __name__)


def log_activity(action):
    activity = Activity(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        path=request.path,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    db.session.add(activity)
    db.session.commit()


@main_bp.route("/")
def home():
    log_activity("Viewed home")

    products = [
        {
            "title": "Web Development",
            "text": "Modern websites and web applications.",
            "icon": "💻",
        },
        {
            "title": "AI Solutions",
            "text": "Practical AI assistants and automation projects.",
            "icon": "🤖",
        },
        {
            "title": "Digital Services",
            "text": "Data, content and technical services for clients.",
            "icon": "🚀",
        },
        {
            "title": "Learning Resources",
            "text": "Tutorials, guides and technology articles.",
            "icon": "📚",
        },
    ]

    return render_template(
        "main/home.html",
        products=products
    )

@main_bp.route("/portfolio")
def portfolio():
    return render_template("main/portfolio.html")


@main_bp.route("/about")
def about():
    log_activity("Viewed about")

    return render_template("main/about.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash(
                "Please fill in your name, email and message.",
                "error"
            )

            return render_template(
                "main/contact.html",
                name=name,
                email=email,
                phone=phone,
                message=message
            )

        if "@" not in email or "." not in email:
            flash(
                "Please enter a valid email address.",
                "error"
            )

            return render_template(
                "main/contact.html",
                name=name,
                email=email,
                phone=phone,
                message=message
            )

        log_activity("Contact form submitted")

        # The form itself is handled successfully.
        # The page will provide Email and WhatsApp contact options
        # using the submitted information.

        return render_template(
            "main/contact.html",
            submitted=True,
            name=name,
            email=email,
            phone=phone,
            message=message
        )

    log_activity("Viewed contact")

    return render_template("main/contact.html")


@main_bp.route("/support")
@login_required
def support():

    tickets = (
        SupportTicket.query
        .filter_by(user_id=current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .all()
    )

    return render_template(
        "support/index.html",
        tickets=tickets
    )


@main_bp.route("/support/new", methods=["GET", "POST"])
@login_required
def new_support_ticket():

    if request.method == "POST":

        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not subject or not message:

            flash(
                "Please enter both a subject and message.",
                "error"
            )

            return render_template("support/new.html")

        ticket = SupportTicket(
            user_id=current_user.id,
            subject=subject,
            message=message,
            status="open"
        )

        db.session.add(ticket)

        db.session.flush()

        activity = Activity(
            user_id=current_user.id,
            action="support_ticket_created",
            path=f"/support/{ticket.id}"
        )

        db.session.add(activity)

        db.session.commit()

        flash(
            "Your support ticket has been created.",
            "success"
        )

        return redirect(
            url_for(
                "main.support_ticket",
                ticket_id=ticket.id
            )
        )

    return render_template("support/new.html")


@main_bp.route("/support/<int:ticket_id>")
@login_required
def support_ticket(ticket_id):

    ticket = db.get_or_404(
        SupportTicket,
        ticket_id
    )

    if (
        ticket.user_id != current_user.id
        and not current_user.is_admin
    ):

        flash(
            "You do not have permission to view this ticket.",
            "error"
        )

        return redirect(
            url_for("main.support")
        )

    replies = (
        SupportReply.query
        .filter_by(ticket_id=ticket.id)
        .order_by(SupportReply.created_at.asc())
        .all()
    )

    return render_template(
        "support/ticket.html",
        ticket=ticket,
        replies=replies
    )


@main_bp.route(
    "/support/<int:ticket_id>/reply",
    methods=["POST"]
)
@login_required
def support_reply(ticket_id):

    ticket = db.get_or_404(
        SupportTicket,
        ticket_id
    )

    if ticket.user_id != current_user.id:

        flash(
            "You do not have permission to reply to this ticket.",
            "error"
        )

        return redirect(
            url_for("main.support")
        )

    if ticket.status in {"closed", "resolved"}:

        flash(
            "This ticket is closed and cannot receive new replies.",
            "error"
        )

        return redirect(
            url_for(
                "main.support_ticket",
                ticket_id=ticket.id
            )
        )

    message = request.form.get(
        "message",
        ""
    ).strip()

    if not message:

        flash(
            "Please enter a message.",
            "error"
        )

        return redirect(
            url_for(
                "main.support_ticket",
                ticket_id=ticket.id
            )
        )

    reply = SupportReply(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=message,
        is_admin=False
    )

    db.session.add(reply)

    activity = Activity(
        user_id=current_user.id,
        action="support_ticket_reply",
        path=f"/support/{ticket.id}"
    )

    db.session.add(activity)

    ticket.status = "open"

    db.session.commit()

    flash(
        "Your reply has been sent.",
        "success"
    )

    return redirect(
        url_for(
            "main.support_ticket",
            ticket_id=ticket.id
        )
    )

