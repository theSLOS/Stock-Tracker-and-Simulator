import json
import os

_KEYS_FILENAME = "api_keys.json"


def _keys_path(username: str) -> str:
    return os.path.join("Users", username, _KEYS_FILENAME)


def get_all_keys(username: str) -> dict:
    path = _keys_path(username)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def get_key(username: str, key_name: str) -> str | None:
    value = get_all_keys(username).get(key_name)
    if value:
        return value
    return os.getenv(key_name) or None


def set_key(username: str, key_name: str, value: str) -> None:
    path = _keys_path(username)
    keys = get_all_keys(username)
    keys[key_name] = value
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(keys, f, indent=4)


def delete_key(username: str, key_name: str) -> None:
    keys = get_all_keys(username)
    if key_name in keys:
        keys.pop(key_name)
        path = _keys_path(username)
        with open(path, "w") as f:
            json.dump(keys, f, indent=4)
