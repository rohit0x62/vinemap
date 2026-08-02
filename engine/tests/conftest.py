import textwrap

import pytest


@pytest.fixture
def project(tmp_path):
    """A tiny multi-language project."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "auth.py").write_text(textwrap.dedent('''
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
    '''))
    (tmp_path / "app" / "db.py").write_text(textwrap.dedent('''
        USERS = {}

        def get_user(username: str):
            return USERS.get(username)
    '''))
    (tmp_path / "web.ts").write_text(textwrap.dedent('''
        import { login } from "./app/auth";

        export function handleLogin(req: Request): Response {
            return new Response("ok");
        }

        export class ApiServer {
            start() {}
        }
    '''))
    return str(tmp_path)
