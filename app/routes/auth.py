import secrets
import smtplib

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from ..extensions import db
from ..extensions import login_manager

from ..models.user import User
from ..models.activity import Activity


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


# =========================================
# LOGIN MANAGER
# =========================================

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id),
    )


# =========================================
# ACTIVITY LOGGING
# =========================================

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


# =========================================
# SEND PASSWORD RESET EMAIL
# =========================================

def send_reset_email(
    user,
    reset_url,
):

    mail_server = current_app.config.get(
        "MAIL_SERVER",
        "smtp.gmail.com",
    )

    mail_port = current_app.config.get(
        "MAIL_PORT",
        587,
    )

    mail_username = current_app.config.get(
        "MAIL_USERNAME",
        "",
    )

    mail_password = current_app.config.get(
        "MAIL_PASSWORD",
        "",
    )

    mail_default_sender = current_app.config.get(
        "MAIL_DEFAULT_SENDER",
        "",
    )

    if not mail_username or not mail_password:

        current_app.logger.error(
            "Email credentials are not configured."
        )

        return False

    sender = (
        mail_default_sender
        or mail_username
    )

    message = EmailMessage()

    message["Subject"] = (
        "SAMTECH SOLUTIONS - Password Reset"
    )

    message["From"] = sender
    message["To"] = user.email

    message.set_content(
        f"""
Hello {user.username},

We received a request to reset the password
for your SAMTECH SOLUTIONS account.

Use the link below to create a new password:

{reset_url}

This link will expire in 30 minutes.

If you did not request a password reset,
you can safely ignore this email.

Regards,

SAMTECH SOLUTIONS
"""
    )

    try:

        with smtplib.SMTP(
            mail_server,
            mail_port,
            timeout=20,
        ) as smtp:

            smtp.ehlo()

            if current_app.config.get(
                "MAIL_USE_TLS",
                True,
            ):

                smtp.starttls()
                smtp.ehlo()

            smtp.login(
                mail_username,
                mail_password,
            )

            smtp.send_message(
                message
            )

        return True

    except Exception:

        current_app.logger.exception(
            "Failed to send password reset email."
        )

        return False


# =========================================
# REGISTER
# =========================================

@auth_bp.route(
    "/register",
    methods=["GET", "POST"],
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        if (
            not username
            or not email
            or len(password) < 8
        ):

            flash(
                "Enter all fields; password must be at least 8 characters.",
                "error",
            )

            return render_template(
                "auth/register.html"
            )

        existing_user = (
            User.query
            .filter(
                (User.username == username)
                | (User.email == email)
            )
            .first()
        )

        if existing_user:

            flash(
                "Username or email already exists.",
                "error",
            )

            return render_template(
                "auth/register.html"
            )

        user = User(
            username=username,
            email=email,
        )

        user.set_password(
            password
        )

        db.session.add(user)

        db.session.commit()

        login_user(user)

        record(
            "Registered account"
        )

        return redirect(
            url_for("main.home")
        )

    return render_template(
        "auth/register.html"
    )


# =========================================
# LOGIN
# =========================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        password = request.form.get(
            "password",
            "",
        )

        user = (
            User.query
            .filter_by(email=email)
            .first()
        )

        if (
            user
            and user.is_active
            and user.check_password(password)
        ):

            login_user(user)

            record(
                "Logged in"
            )

            return redirect(
                url_for("main.home")
            )

        flash(
            "Invalid email or password.",
            "error",
        )

    return render_template(
        "auth/login.html"
    )


# =========================================
# FORGOT PASSWORD
# =========================================

@auth_bp.route(
    "/forgot-password",
    methods=["GET", "POST"],
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        user = (
            User.query
            .filter_by(email=email)
            .first()
        )

        # Always show the same message.
        # This prevents revealing whether
        # an email address is registered.

        if user:

            token = secrets.token_urlsafe(
                48
            )

            expires_at = (
                datetime.now(timezone.utc)
                + timedelta(minutes=30)
            )

            user.reset_token = token

            user.reset_token_expires = (
                expires_at
            )

            db.session.commit()

            reset_url = url_for(
                "auth.reset_password",
                token=token,
                _external=True,
            )

            email_sent = send_reset_email(
                user,
                reset_url,
            )

            if not email_sent:

                current_app.logger.error(
                    "Password reset email could not be sent."
                )

        flash(
            "If an account exists with that email, a password reset link has been sent.",
            "success",
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/forgot_password.html"
    )


# =========================================
# RESET PASSWORD
# =========================================

@auth_bp.route(
    "/reset-password/<token>",
    methods=["GET", "POST"],
)
def reset_password(token):

    user = (
        User.query
        .filter_by(reset_token=token)
        .first()
    )

    if not user:

        flash(
            "This password reset link is invalid or has expired.",
            "error",
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    expires_at = user.reset_token_expires

    if not expires_at:

        flash(
            "This password reset link is invalid or has expired.",
            "error",
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    # SQLite may return the stored datetime
    # without timezone information.
    # Treat it as UTC before comparing it
    # with the current UTC time.

    if expires_at.tzinfo is None:

        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= datetime.now(timezone.utc):

        user.reset_token = None
        user.reset_token_expires = None

        db.session.commit()

        flash(
            "This password reset link is invalid or has expired.",
            "error",
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    if request.method == "POST":

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirm_password",
            "",
        )

        if len(password) < 8:

            flash(
                "Password must be at least 8 characters.",
                "error",
            )

            return render_template(
                "auth/reset_password.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error",
            )

            return render_template(
                "auth/reset_password.html"
            )

        user.set_password(
            password
        )

        # Invalidate the token immediately
        # after a successful password change.

        user.reset_token = None
        user.reset_token_expires = None

        db.session.commit()

        flash(
            "Your password has been reset successfully. You can now log in.",
            "success",
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/reset_password.html"
    )


# =========================================
# LOGOUT
# =========================================

@auth_bp.route(
    "/logout"
)
@login_required
def logout():

    record(
        "Logged out"
    )

    logout_user()

    return redirect(
        url_for("main.home")
    )