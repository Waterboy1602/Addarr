import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class TranslationStub:
    values = {
        "addarr.Series": "Series",
        "addarr.SeriesWithArticle": "The series",
        "addarr.Sport": "Sport",
        "addarr.SportWithArticle": "The league",
    }

    def t(self, key):
        return self.values[key]


def load_serie_or_sport_article():
    source_path = Path(__file__).parents[1] / "src" / "addarr.py"
    source = ast.parse(source_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in source.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "serieOrSportArticle"
    )
    namespace = {"i18n": TranslationStub()}
    exec(compile(ast.Module([function], []), source_path, "exec"), namespace)
    return namespace["serieOrSportArticle"]


class SerieOrSportArticleTest(unittest.TestCase):
    def setUp(self):
        self.article = load_serie_or_sport_article()

    def test_series_returns_series_wording(self):
        context = SimpleNamespace(user_data={"choice": "Series"})

        self.assertEqual("The series", self.article(context))

    def test_sport_returns_sport_wording(self):
        context = SimpleNamespace(user_data={"choice": "Sport"})

        self.assertEqual("The league", self.article(context))


if __name__ == "__main__":
    unittest.main()
