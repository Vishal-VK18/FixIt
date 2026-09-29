"""Create an administrator account through a controlled backend command."""

from getpass import getpass

import auth_service
import db


def main() -> None:
    db.init_db()
    print("CampusCare administrator setup")
    name = input("Name: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password (minimum 8 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        user = auth_service.create_user(name, email, password, "admin")
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Administrator created: {user['email']}")


if __name__ == "__main__":
    main()
