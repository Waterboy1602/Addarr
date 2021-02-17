import yaml
from definitions import CONFIG_PATH, DEFAULT_SETTINGS

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))

for setting, default_value in DEFAULT_SETTINGS.items():
    if setting not in config:
        config[setting] = default_value

