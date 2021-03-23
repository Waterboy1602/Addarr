import i18n

from config import config
from definitions import LANG_PATH

i18n.load_path.append(LANG_PATH)
i18n.set('locale', config["language"])
