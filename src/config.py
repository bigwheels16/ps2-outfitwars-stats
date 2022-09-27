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


def DB_HOST():
    return get_env_string("DB_HOST")

def DB_PORT():
    return get_env_string("DB_PORT")

def DB_USERNAME():
    return get_env_string("DB_USERNAME")

def DB_PASSWORD():
    return get_env_string("DB_PASSWORD")

def DB_DATABASE():
    return get_env_string("DB_DATABASE")

def BASE_URL_PATH():
    return get_env_string("BASE_URL_PATH")
