import os


def get_database_url():

    url = os.getenv(
        "DATABASE_URL",
        "sqlite:///site.db"
    ).strip()

    # Some hosted PostgreSQL providers still return
    # the legacy postgres:// scheme.

    if url.startswith("postgres://"):

        url = (
            "postgresql+psycopg://"
            + url[len("postgres://"):]
        )

    elif url.startswith("postgresql://"):

        url = (
            "postgresql+psycopg://"
            + url[len("postgresql://"):]
        )

    return url


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = get_database_url()

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    API_KEY = os.getenv(
        "API_KEY",
        ""
    )


    # =========================================
    # ADMIN
    # =========================================

    ADMIN_USERNAME = os.getenv(
        "ADMIN_USERNAME",
        "Samapiyo"
    )

    ADMIN_EMAIL = os.getenv(
        "ADMIN_EMAIL",
        ""
    )

    ADMIN_PASSWORD = os.getenv(
        "ADMIN_PASSWORD",
        ""
    )


    # =========================================
    # EMAIL / PASSWORD RESET
    # =========================================

    MAIL_SERVER = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USE_TLS = os.getenv(
        "MAIL_USE_TLS",
        "1"
    ) == "1"

    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME",
        ""
    )

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD",
        ""

    )

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        ""
    )


    # =========================================
    # M-PESA
    # =========================================

    MPESA_CONSUMER_KEY = os.getenv(
        "MPESA_CONSUMER_KEY",
        ""
    )

    MPESA_CONSUMER_SECRET = os.getenv(
        "MPESA_CONSUMER_SECRET",
        ""
    )

    MPESA_SHORTCODE = os.getenv(
        "MPESA_SHORTCODE",
        ""
    )

    MPESA_PASSKEY = os.getenv(
        "MPESA_PASSKEY",
        ""
    )

    MPESA_CALLBACK_URL = os.getenv(
        "MPESA_CALLBACK_URL",
        ""
    )

    MPESA_ENV = os.getenv(
        "MPESA_ENV",
        "sandbox"
    ).lower()

    MPESA_TRANSACTION_TYPE = os.getenv(
        "MPESA_TRANSACTION_TYPE",
        "CustomerPayBillOnline"
    )


    # =========================================
    # SESSION SECURITY
    # =========================================

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = os.getenv(
        "SESSION_COOKIE_SECURE",
        "0"
    ) == "1"