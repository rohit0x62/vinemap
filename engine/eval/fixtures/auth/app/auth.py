"""Authentication helpers."""
from app.db import get_user


def hash_password(password: str, salt: str = "") -> str:
    """Hash a password with the given salt."""
    return password + salt


def login(username: str, password: str) -> bool:
    user = get_user(username)
    return user is not None and hash_password(password) == user


class SessionManager:
    def create_session(self, user_id: int) -> str:
        return str(user_id)
