from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models.user import User
from ..models.activity import Activity
from ..extensions import login_manager

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def record(action):
    db.session.add(Activity(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        path=request.path,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
    ))
    db.session.commit()

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not username or not email or len(password) < 8:
            flash("Enter all fields; password must be at least 8 characters.", "error")
            return render_template("auth/register.html")
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "error")
            return render_template("auth/register.html")
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        record("Registered account")
        return redirect(url_for("main.home"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            record("Logged in")
            return redirect(url_for("main.home"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    record("Logged out")
    logout_user()
    return redirect(url_for("main.home"))
