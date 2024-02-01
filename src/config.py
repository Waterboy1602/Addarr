import yaml

from definitions import CONFIG_PATH, CONFIG_EXAMPLE_PATH, DEFAULT_SETTINGS

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))
config_example = yaml.safe_load(open(CONFIG_EXAMPLE_PATH, encoding="utf8"))


for setting, default_value in DEFAULT_SETTINGS.items():
    if setting not in config:
        config[setting] = default_value


def flatten_dict(dd, separator ='/', prefix =''):
    return { prefix + separator + k if prefix else k : v
             for kk, vv in dd.items()
             for k, v in flatten_dict(vv, separator, kk).items()
             } if isinstance(dd, dict) else { prefix : dd }


def checkConfig():
    missingConfig=[]
    for key_ex, value_ex in flatten_dict(config_example).items():
        if key_ex not in flatten_dict(config):
            missingConfig.append(key_ex)
    return missingConfig


def checkConfigValues():
    wrongValues = []
    languages = ["de-de", "en-us", "es-es", "fr-fr", "it-it", "nl-be", "pl-pl", "pt-pt", "ru-ru"]
    if config["language"] not in languages:
        wrongValues.append("language")
    return wrongValues
