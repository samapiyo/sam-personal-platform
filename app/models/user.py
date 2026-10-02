from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from ..extensions import db


class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    email = db.Column(
        db.String(160),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    reset_token = db.Column(
        db.String(255),
        unique=True,
        nullable=True,
    )

    reset_token_expires = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    activities = db.relationship(
        "Activity",
        backref="user",
        lazy=True,
    )

    def set_password(
        self,
        password,
    ):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(
        self,
        password,
    ):

        return check_password_hash(
            self.password_hash,
            password,
        )