import _bootstrap  # noqa: I001
import json
from types import SimpleNamespace

import pytest

from manga_translator.translators.common import ISO_639_1_TO_VALID_LANGUAGES, VALID_LANGUAGES
from manga_translator.utils.textblock import LANGUAGE_ORIENTATION_PRESETS
from services.translation_service import TranslationService

ROOT = _bootstrap.ROOT
LOCALE_DIR = ROOT / "desktop_qt_ui" / "locales"
LOCALES = ("zh_CN", "zh_TW", "en_US", "ja_JP", "ko_KR", "es_ES", "ru_RU")


def test_uzbek_target_language_asks_for_latin_script():
    # The name is substituted into the LLM system prompt, so it has to pin the script.
    assert VALID_LANGUAGES["UZB"] == "Uzbek (Latin script)"


def test_uzbek_iso_code_maps_to_uzb():
    assert ISO_639_1_TO_VALID_LANGUAGES["uz"] == "UZB"


def test_uzbek_renders_horizontally():
    assert LANGUAGE_ORIENTATION_PRESETS["UZB"] == "h"


def test_desktop_target_language_menu_offers_uzbek():
    service = SimpleNamespace(_t=lambda key: key)

    languages = TranslationService.get_target_languages(service)

    assert languages["UZB"] == "lang_UZB"


@pytest.mark.parametrize("locale", LOCALES)
def test_every_locale_names_uzbek(locale):
    catalog = json.loads((LOCALE_DIR / f"{locale}.json").read_text(encoding="utf-8"))

    assert catalog.get("lang_UZB", "").strip()
