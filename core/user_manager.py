import os
import json

USERS_DIR = os.path.join(os.path.dirname(__file__), '..', 'Users')


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
        "password": password,
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
