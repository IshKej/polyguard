"""
The full PolyGuard language catalog.

This is the target list PolyGuard aims to cover: the world's languages that have
enough digital presence to (a) be written by real users and (b) be translated with
usable quality. It spans the resource spectrum on purpose, because the whole point
is to compare how well bots are defended in high-resource vs low-resource languages.

tier: DERIVED, never hand-assigned.

The tier is the independent variable of the entire study, so it must not be an
opinion. Each language carries `joshi`, its class in Joshi et al. (2020), "The
State and Fate of Linguistic Diversity and Inclusion in the NLP World" (ACL
2020), read from the paper's own published mapping at
https://microsoft.github.io/linguisticdiversity/assets/lang2tax.txt

The tier follows from that class by one stated rule, applied with no exceptions:

  high  Joshi class 4-5   ("the winners" and "the underdogs")
  mid   Joshi class 3     ("the rising stars")
  low   Joshi class 0-2   the languages the field has left behind

Hand-assigned tiers were used until 2026-09-23 and were wrong in both directions:
class-3 languages sat in BOTH mid and low, Basque (class 4) sat in low, and Telugu
(class 1) sat in mid. That contaminates the variable the whole finding rests on.

Known anomaly, deliberately NOT overridden: Joshi puts Kyrgyz in class 4, which
does not match its actual standing. Hand-adjusting the independent variable to
match intuition is exactly the freedom that lets a result be steered, so the
published class is kept and the anomaly is named here instead. The capability
controls exist to catch a language the model cannot really operate in.

Languages already hand-authored and verified in generate_attack_bank.py are marked
authored=True here. expand_languages.py translates the rest through the Anthropic API and appends
them to attack_bank.json flagged verified=False.
"""

CATALOG = {
    # ---- already hand-authored + verified ----
    "en": {"name": "English",     "native": "English",          "tier": "high", "authored": True, "joshi": 5},
    "es": {"name": "Spanish",     "native": "Español",          "tier": "high", "authored": True, "joshi": 5},
    "hi": {"name": "Hindi",       "native": "हिन्दी",             "tier": "high", "authored": True, "joshi": 4},
    "gu": {"name": "Gujarati",    "native": "ગુજરાતી",           "tier": "high",  "authored": True, "joshi": 4},
    "zh": {"name": "Chinese",     "native": "中文",              "tier": "high", "authored": True, "joshi": 5},
    "tl": {"name": "Tagalog",     "native": "Tagalog",          "tier": "mid",  "authored": True, "joshi": 3},
    "vi": {"name": "Vietnamese",  "native": "Tiếng Việt",       "tier": "high",  "authored": True, "joshi": 4},
    "ar": {"name": "Arabic",      "native": "العربية",           "tier": "high", "authored": True, "joshi": 5},
    "ko": {"name": "Korean",      "native": "한국어",            "tier": "high", "authored": True, "joshi": 4},
    "fr": {"name": "French",      "native": "Français",         "tier": "high", "authored": True, "joshi": 5},
    "ru": {"name": "Russian",     "native": "Русский",          "tier": "high", "authored": True, "joshi": 4},
    "pt": {"name": "Portuguese",  "native": "Português",        "tier": "high", "authored": True, "joshi": 4},
    "de": {"name": "German",      "native": "Deutsch",          "tier": "high", "authored": True, "joshi": 5},
    "it": {"name": "Italian",     "native": "Italiano",         "tier": "high", "authored": True, "joshi": 4},
    "ja": {"name": "Japanese",    "native": "日本語",            "tier": "high", "authored": True, "joshi": 5},
    "pl": {"name": "Polish",      "native": "Polski",           "tier": "high", "authored": True, "joshi": 4},
    "tr": {"name": "Turkish",     "native": "Türkçe",           "tier": "high",  "authored": True, "joshi": 4},
    "id": {"name": "Indonesian",  "native": "Bahasa Indonesia", "tier": "mid",  "authored": True, "joshi": 3},
    "uk": {"name": "Ukrainian",   "native": "Українська",       "tier": "mid",  "authored": True, "joshi": 3},
    "el": {"name": "Greek",       "native": "Ελληνικά",         "tier": "mid",  "authored": True, "joshi": 3},

    # ---- European ----
    "nl": {"name": "Dutch",       "native": "Nederlands",       "tier": "high", "joshi": 4},
    "sv": {"name": "Swedish",     "native": "Svenska",          "tier": "high", "joshi": 4},
    "no": {"name": "Norwegian",   "native": "Norsk",            "tier": "high", "joshi": 4},
    "da": {"name": "Danish",      "native": "Dansk",            "tier": "mid", "joshi": 3},
    "fi": {"name": "Finnish",     "native": "Suomi",            "tier": "high", "joshi": 4},
    "cs": {"name": "Czech",       "native": "Čeština",          "tier": "high", "joshi": 4},
    "sk": {"name": "Slovak",      "native": "Slovenčina",       "tier": "mid", "joshi": 3},
    "hu": {"name": "Hungarian",   "native": "Magyar",           "tier": "high", "joshi": 4},
    "ro": {"name": "Romanian",    "native": "Română",           "tier": "mid", "joshi": 3},
    "bg": {"name": "Bulgarian",   "native": "Български",         "tier": "mid", "joshi": 3},
    "hr": {"name": "Croatian",    "native": "Hrvatski",         "tier": "high", "joshi": 4},
    "sr": {"name": "Serbian",     "native": "Српски",           "tier": "high", "joshi": 4},
    "sl": {"name": "Slovenian",   "native": "Slovenščina",      "tier": "mid", "joshi": 3},
    "lt": {"name": "Lithuanian",  "native": "Lietuvių",         "tier": "mid", "joshi": 3},
    "lv": {"name": "Latvian",     "native": "Latviešu",         "tier": "mid", "joshi": 3},
    "et": {"name": "Estonian",    "native": "Eesti",            "tier": "mid", "joshi": 3},
    "mk": {"name": "Macedonian",  "native": "Македонски",       "tier": "low", "joshi": 1},
    "sq": {"name": "Albanian",    "native": "Shqip",            "tier": "low", "joshi": 1},
    "is": {"name": "Icelandic",   "native": "Íslenska",         "tier": "low", "joshi": 2},
    "ga": {"name": "Irish",       "native": "Gaeilge",          "tier": "low", "joshi": 2},
    "cy": {"name": "Welsh",       "native": "Cymraeg",          "tier": "low", "joshi": 1},
    "eu": {"name": "Basque",      "native": "Euskara",          "tier": "high", "joshi": 4},
    "ca": {"name": "Catalan",     "native": "Català",           "tier": "high", "joshi": 4},
    "gl": {"name": "Galician",    "native": "Galego",           "tier": "mid", "joshi": 3},

    # ---- Middle East / Central Asia ----
    "he": {"name": "Hebrew",      "native": "עברית",             "tier": "mid", "joshi": 3},
    "fa": {"name": "Persian",     "native": "فارسی",             "tier": "high", "joshi": 4},
    "ps": {"name": "Pashto",      "native": "پښتو",              "tier": "low", "joshi": 2},
    "az": {"name": "Azerbaijani", "native": "Azərbaycan",       "tier": "low", "joshi": 1},
    "kk": {"name": "Kazakh",      "native": "Қазақ",            "tier": "mid", "joshi": 3},
    "uz": {"name": "Uzbek",       "native": "Oʻzbek",            "tier": "mid", "joshi": 3},
    "ky": {"name": "Kyrgyz",      "native": "Кыргыз",           "tier": "high", "joshi": 4},
    "tg": {"name": "Tajik",       "native": "Тоҷикӣ",           "tier": "low", "joshi": 1},
    "mn": {"name": "Mongolian",   "native": "Монгол",           "tier": "low", "joshi": 1},
    "ka": {"name": "Georgian",    "native": "ქართული",          "tier": "mid", "joshi": 3},
    "hy": {"name": "Armenian",    "native": "Հայերեն",          "tier": "low", "joshi": 1},

    # ---- South Asia ----
    "bn": {"name": "Bengali",     "native": "বাংলা",             "tier": "mid", "joshi": 3},
    "ur": {"name": "Urdu",        "native": "اردو",              "tier": "mid", "joshi": 3},
    "pa": {"name": "Punjabi",     "native": "ਪੰਜਾਬੀ",            "tier": "low", "joshi": 2},
    "ta": {"name": "Tamil",       "native": "தமிழ்",             "tier": "mid", "joshi": 3},
    "te": {"name": "Telugu",      "native": "తెలుగు",            "tier": "low", "joshi": 1},
    "mr": {"name": "Marathi",     "native": "मराठी",             "tier": "low", "joshi": 2},
    "kn": {"name": "Kannada",     "native": "ಕನ್ನಡ",             "tier": "low", "joshi": 1},
    "ml": {"name": "Malayalam",   "native": "മലയാളം",           "tier": "low", "joshi": 1},
    "or": {"name": "Odia",        "native": "ଓଡ଼ିଆ",              "tier": "low", "joshi": 1},
    "ne": {"name": "Nepali",      "native": "नेपाली",            "tier": "low", "joshi": 1},
    "si": {"name": "Sinhala",     "native": "සිංහල",            "tier": "low", "joshi": 1},

    # ---- Southeast / East Asia ----
    "th": {"name": "Thai",        "native": "ไทย",               "tier": "mid", "joshi": 3},
    "ms": {"name": "Malay",       "native": "Bahasa Melayu",    "tier": "mid", "joshi": 3},
    "km": {"name": "Khmer",       "native": "ខ្មែរ",              "tier": "low", "joshi": 1},
    "lo": {"name": "Lao",         "native": "ລາວ",               "tier": "low", "joshi": 2},
    "my": {"name": "Burmese",     "native": "မြန်မာ",             "tier": "low", "joshi": 1},
    "jv": {"name": "Javanese",    "native": "Basa Jawa",        "tier": "low", "joshi": 1},
    "su": {"name": "Sundanese",   "native": "Basa Sunda",       "tier": "low", "joshi": 1},
    "ceb": {"name": "Cebuano",    "native": "Cebuano",          "tier": "mid", "joshi": 3},

    # ---- Africa ----
    "sw": {"name": "Swahili",     "native": "Kiswahili",        "tier": "low", "joshi": 2},
    "am": {"name": "Amharic",     "native": "አማርኛ",             "tier": "low", "joshi": 2},
    "ha": {"name": "Hausa",       "native": "Hausa",            "tier": "low", "joshi": 2},
    "yo": {"name": "Yoruba",      "native": "Yoruba",           "tier": "low", "joshi": 2},
    "ig": {"name": "Igbo",        "native": "Igbo",             "tier": "low", "joshi": 1},
    "zu": {"name": "Zulu",        "native": "isiZulu",          "tier": "low", "joshi": 2},
    "xh": {"name": "Xhosa",       "native": "isiXhosa",         "tier": "low", "joshi": 2},
    "so": {"name": "Somali",      "native": "Soomaali",         "tier": "low", "joshi": 1},
    "sn": {"name": "Shona",       "native": "chiShona",         "tier": "low", "joshi": 1},
    "rw": {"name": "Kinyarwanda", "native": "Kinyarwanda",      "tier": "low", "joshi": 1},
    "ny": {"name": "Chichewa",    "native": "Chichewa",         "tier": "low", "joshi": 1},

    # ---- Other ----
    "af": {"name": "Afrikaans",   "native": "Afrikaans",        "tier": "mid", "joshi": 3},
    "ht": {"name": "Haitian Creole", "native": "Kreyòl ayisyen","tier": "low", "joshi": 2},
}

# Convenience groupings
AUTHORED = [c for c, m in CATALOG.items() if m.get("authored")]
PENDING = [c for c, m in CATALOG.items() if not m.get("authored")]


def tier_of(code: str) -> str:
    return CATALOG.get(code, {}).get("tier", "mid")


if __name__ == "__main__":
    from collections import Counter
    print(f"catalog: {len(CATALOG)} languages")
    print(f"authored/verified: {len(AUTHORED)}")
    print(f"pending generation: {len(PENDING)}")
    print("by tier:", dict(Counter(m["tier"] for m in CATALOG.values())))
