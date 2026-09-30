import os
from dotenv import load_dotenv

# Load .env BEFORE importing Config
load_dotenv()

from flask import Flask
from .config import Config
from .extensions import db, login_manager

# Load local .env when developing. Render uses its Environment Variables instead.
load_dotenv()


def ensure_admin():
    from .models.user import User

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_username = os.getenv("ADMIN_USERNAME", "Samapiyo").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_email or not admin_password:
        raise RuntimeError(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be configured."
        )

    user = User.query.filter_by(email=admin_email).first()

    if user is None:
        user = User(
            username=admin_username,
            email=admin_email,
            is_admin=True,
        )

        user.set_password(admin_password)

        db.session.add(user)
        db.session.commit()

        print(f"Admin account created: {admin_email}")

    else:
        changed = False

        if not user.is_admin:
            user.is_admin = True
            changed = True

        if changed:
            db.session.commit()

        print(f"Admin account verified: {admin_email}")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Never silently run production with a known/default secret.
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "dev-only-change-me"

        if os.getenv("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY must be set in production.")

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.blog import blog_bp
    from .routes.business import business_bp
    from .routes.opportunities import opportunities_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(business_bp)
    app.register_blueprint(opportunities_bp)

    with app.app_context():
        from . import models

        db.create_all()

        # Ensure the deployment always has the configured administrator.
        ensure_admin()

        # Stage 3 adds BlogPost.category.
        # This compatibility migration keeps an existing
        # Stage 2 SQLite/PostgreSQL database usable.
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)

        columns = {
            column["name"]
            for column in inspector.get_columns("blog_post")
        }

        if "category" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE blog_post "
                    "ADD COLUMN category VARCHAR(100) "
                    "NOT NULL DEFAULT 'General'"
                )
            )

            db.session.commit()

    return app