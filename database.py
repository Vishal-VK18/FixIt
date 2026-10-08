"""Deprecated Streamlit database interface; db.py is the sole ticket store."""


def init_db() -> None:
    raise RuntimeError("The legacy database is retired. Use the FastAPI app and db.py.")


def get_db_session():
    raise RuntimeError("The legacy database is retired. Use the FastAPI app and db.py.")


def get_db_connection():
    raise RuntimeError("The legacy database is retired. Use the FastAPI app and db.py.")
