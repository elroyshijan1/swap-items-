import os

# Pull from environment variables if set, otherwise use these defaults.
# On your Mac, set these in terminal before running the app, e.g.:
#   export DB_PASSWORD="your_mysql_password"
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "swapshelf_db"),
}

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this")

# From Google Cloud Console > APIs & Services > Credentials.
# Leave unset and the Google button just won't appear.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")