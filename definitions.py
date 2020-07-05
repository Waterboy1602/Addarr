import os

# Set Projects Root Directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set Projects Configuration path
CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")
LANG_PATH = os.path.join(ROOT_DIR, "lang.yaml")
CHATID_PATH = os.path.join(ROOT_DIR, "chatid.txt")
LOG_PATH = os.path.join(ROOT_DIR, "logs", "addarr.log")
ADMIN_PATH = os.path.join(ROOT_DIR, "admin.txt")
