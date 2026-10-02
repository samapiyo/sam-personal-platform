import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parent
    / "instance"
    / "site.db"
)


def main():

    if not DATABASE_PATH.exists():

        print(
            f"Database not found: {DATABASE_PATH}"
        )

        return


    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()


    cursor.execute(
        "PRAGMA table_info(user)"
    )

    columns = {
        row[1]
        for row in cursor.fetchall()
    }


    if "reset_token" not in columns:

        cursor.execute(
            """
            ALTER TABLE user
            ADD COLUMN reset_token VARCHAR(255)
            """
        )

        print(
            "Added reset_token column."
        )

    else:

        print(
            "reset_token already exists."
        )


    if "reset_token_expires" not in columns:

        cursor.execute(
            """
            ALTER TABLE user
            ADD COLUMN reset_token_expires DATETIME
            """
        )

        print(
            "Added reset_token_expires column."
        )

    else:

        print(
            "reset_token_expires already exists."
        )


    connection.commit()


    cursor.execute(
        "PRAGMA table_info(user)"
    )

    updated_columns = {
        row[1]
        for row in cursor.fetchall()
    }


    connection.close()


    print()
    print(
        "Password-reset database migration complete."
    )

    print(
        "reset_token:",
        "OK"
        if "reset_token" in updated_columns
        else "MISSING",
    )

    print(
        "reset_token_expires:",
        "OK"
        if "reset_token_expires" in updated_columns
        else "MISSING",
    )


if __name__ == "__main__":

    main()