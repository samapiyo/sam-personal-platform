import os

from sqlalchemy import create_engine, inspect, text


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured."
    )


# Convert older PostgreSQL URL formats if necessary.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )

elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


engine = create_engine(
    DATABASE_URL
)


with engine.connect() as connection:

    inspector = inspect(connection)

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "user"
        )
    }

    print("Checking production PostgreSQL database...")
    print()

    if "reset_token" not in columns:

        connection.execute(
            text(
                'ALTER TABLE "user" '
                'ADD COLUMN reset_token VARCHAR(255)'
            )
        )

        print(
            "Added reset_token column."
        )

    else:

        print(
            "reset_token already exists."
        )


    if "reset_token_expires" not in columns:

        connection.execute(
            text(
                'ALTER TABLE "user" '
                'ADD COLUMN reset_token_expires TIMESTAMP'
            )
        )

        print(
            "Added reset_token_expires column."
        )

    else:

        print(
            "reset_token_expires already exists."
        )


    connection.commit()


print()
print(
    "Production password-reset database migration complete."
)