import os


def get_env_bool(name, default=None):
    val = os.environ.get(name)
    if val is None:
        return default
    elif val == "1" or val.lower() == "true":
        return True
    else:
        return False


def get_env_string(name, default=None):
    return os.environ.get(name, default)


def DB_DRIVERNAME():
    return get_env_string("DB_DRIVERNAME")


def DB_USERNAME():
    return get_env_string("DB_USERNAME")


def DB_PASSWORD():
    return get_env_string("DB_PASSWORD")


def DB_NAME():
    return get_env_string("DB_NAME")


def DB_HOST():
    return get_env_string("DB_HOST")


def DB_IP_TYPE():
    return get_env_string("DB_IP_TYPE").upper()
