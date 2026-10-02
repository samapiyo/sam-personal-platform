import sqlite3
from pathlib import Path


database_path = Path("instance") / "site.db"


if not database_path.exists():
    raise FileNotFoundError(
        f"Database not found: {database_path}"
    )


connection = sqlite3.connect(
    database_path
)

cursor = connection.cursor()


cursor.execute(
    "PRAGMA table_info(user)"
)

columns = {
    row[1]
    for row in cursor.fetchall()
}


if "is_active" in columns:

    print(
        "is_active column already exists."
    )

else:

    cursor.execute(
        """
        ALTER TABLE user
        ADD COLUMN is_active BOOLEAN
        NOT NULL
        DEFAULT 1
        """
    )

    connection.commit()

    print(
        "is_active column added successfully."
    )


cursor.execute(
    "PRAGMA table_info(user)"
)

print("\nCurrent user table columns:")

for row in cursor.fetchall():

    print(
        f"- {row[1]} ({row[2]})"
    )


connection.close()