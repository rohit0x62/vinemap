USERS = {}


def get_user(username: str):
    return USERS.get(username)
