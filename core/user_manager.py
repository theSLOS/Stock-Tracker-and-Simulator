import hashlib
import os
import json
import secrets

USERS_DIR = os.path.join(os.path.dirname(__file__), '..', 'Users')

_HASH_PREFIX = "pbkdf2sha256"
_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"{_HASH_PREFIX}:{_ITERATIONS}:{salt}:{dk.hex()}"


def verify_password(stored: str, provided: str) -> bool:
    if not stored.startswith(_HASH_PREFIX + ":"):
        return stored == provided  # legacy plain-text
    parts = stored.split(":")
    if len(parts) != 4:
        return False
    _, iterations, salt, stored_hash = parts
    dk = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt.encode(), int(iterations))
    return secrets.compare_digest(dk.hex(), stored_hash)


def load_users():
    if not os.path.exists(USERS_DIR):
        return {}
    users = {}
    for name in os.listdir(USERS_DIR):
        profile_path = os.path.join(USERS_DIR, name, 'profile.json')
        if os.path.exists(profile_path):
            with open(profile_path) as f:
                users[name] = json.load(f)
    return users


def get_user_dir(username):
    return os.path.join(USERS_DIR, username)


def create_user(username, password):
    user_dir = get_user_dir(username)
    os.makedirs(user_dir, exist_ok=True)
    profile = {
        "username": username,
        "password": hash_password(password),
        "preferences": {
            "theme": "dark",
            "default_stock": "AAPL"
        }
    }
    with open(os.path.join(user_dir, 'profile.json'), 'w') as f:
        json.dump(profile, f, indent=4)


def get_user_profile(username):
    profile_path = os.path.join(get_user_dir(username), 'profile.json')
    with open(profile_path) as f:
        return json.load(f)


def save_user_profile(username, profile):
    profile_path = os.path.join(get_user_dir(username), 'profile.json')
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)


def get_avatar_path(username: str) -> str:
    return os.path.join(get_user_dir(username), "avatar.png")


def rename_user(old_username: str, new_username: str) -> None:
    """Rename user folder and update profile.json. Raises ValueError if new name taken."""
    if os.path.exists(get_user_dir(new_username)):
        raise ValueError(f"Username '{new_username}' is already taken.")
    os.rename(get_user_dir(old_username), get_user_dir(new_username))
    profile = get_user_profile(new_username)
    profile["username"] = new_username
    save_user_profile(new_username, profile)
