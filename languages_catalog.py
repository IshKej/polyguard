"""
The full PolyGuard language catalog.

This is the target list PolyGuard aims to cover: the world's languages that have
enough digital presence to (a) be written by real users and (b) be translated with
usable quality. It spans the resource spectrum on purpose, because the whole point
is to compare how well bots are defended in high-resource vs low-resource languages.

tier:
  high  large training presence, strong safety coverage expected
  mid   moderate presence
  low   low-resource; this is where the equity gap is expected to be worst

Languages already hand-authored and verified in generate_attack_bank.py are marked
authored=True here. expand_languages.py translates the rest via Claude and appends
them to attack_bank.json flagged verified=False.
"""

CATALOG = {
    # ---- already hand-authored + verified ----
    "en": {"name": "English",     "native": "English",          "tier": "high", "authored": True},
    "es": {"name": "Spanish",     "native": "Espanol",          "tier": "high", "authored": True},
    "hi": {"name": "Hindi",       "native": "हिन्दी",             "tier": "high", "authored": True},
    "gu": {"name": "Gujarati",    "native": "ગુજરાતી",           "tier": "mid",  "authored": True},
    "zh": {"name": "Chinese",     "native": "中文",              "tier": "high", "authored": True},
    "tl": {"name": "Tagalog",     "native": "Tagalog",          "tier": "mid",  "authored": True},
    "vi": {"name": "Vietnamese",  "native": "Tieng Viet",       "tier": "mid",  "authored": True},
    "ar": {"name": "Arabic",      "native": "العربية",           "tier": "high", "authored": True},
    "ko": {"name": "Korean",      "native": "한국어",            "tier": "high", "authored": True},
    "fr": {"name": "French",      "native": "Francais",         "tier": "high", "authored": True},
    "ru": {"name": "Russian",     "native": "Русский",          "tier": "high", "authored": True},
    "pt": {"name": "Portuguese",  "native": "Portugues",        "tier": "high", "authored": True},
    "de": {"name": "German",      "native": "Deutsch",          "tier": "high", "authored": True},
    "it": {"name": "Italian",     "native": "Italiano",         "tier": "high", "authored": True},
    "ja": {"name": "Japanese",    "native": "日本語",            "tier": "high", "authored": True},
    "pl": {"name": "Polish",      "native": "Polski",           "tier": "high", "authored": True},
    "tr": {"name": "Turkish",     "native": "Turkce",           "tier": "mid",  "authored": True},
    "id": {"name": "Indonesian",  "native": "Bahasa Indonesia", "tier": "mid",  "authored": True},
    "uk": {"name": "Ukrainian",   "native": "Українська",       "tier": "mid",  "authored": True},
    "el": {"name": "Greek",       "native": "Ελληνικά",         "tier": "mid",  "authored": True},

    # ---- European ----
    "nl": {"name": "Dutch",       "native": "Nederlands",       "tier": "high"},
    "sv": {"name": "Swedish",     "native": "Svenska",          "tier": "mid"},
    "no": {"name": "Norwegian",   "native": "Norsk",            "tier": "mid"},
    "da": {"name": "Danish",      "native": "Dansk",            "tier": "mid"},
    "fi": {"name": "Finnish",     "native": "Suomi",            "tier": "mid"},
    "cs": {"name": "Czech",       "native": "Cestina",          "tier": "mid"},
    "sk": {"name": "Slovak",      "native": "Slovencina",       "tier": "mid"},
    "hu": {"name": "Hungarian",   "native": "Magyar",           "tier": "mid"},
    "ro": {"name": "Romanian",    "native": "Romana",           "tier": "mid"},
    "bg": {"name": "Bulgarian",   "native": "Български",         "tier": "mid"},
    "hr": {"name": "Croatian",    "native": "Hrvatski",         "tier": "mid"},
    "sr": {"name": "Serbian",     "native": "Српски",           "tier": "mid"},
    "sl": {"name": "Slovenian",   "native": "Slovenscina",      "tier": "low"},
    "lt": {"name": "Lithuanian",  "native": "Lietuviu",         "tier": "low"},
    "lv": {"name": "Latvian",     "native": "Latviesu",         "tier": "low"},
    "et": {"name": "Estonian",    "native": "Eesti",            "tier": "low"},
    "mk": {"name": "Macedonian",  "native": "Македонски",       "tier": "low"},
    "sq": {"name": "Albanian",    "native": "Shqip",            "tier": "low"},
    "is": {"name": "Icelandic",   "native": "Islenska",         "tier": "low"},
    "ga": {"name": "Irish",       "native": "Gaeilge",          "tier": "low"},
    "cy": {"name": "Welsh",       "native": "Cymraeg",          "tier": "low"},
    "eu": {"name": "Basque",      "native": "Euskara",          "tier": "low"},
    "ca": {"name": "Catalan",     "native": "Catala",           "tier": "mid"},
    "gl": {"name": "Galician",    "native": "Galego",           "tier": "low"},

    # ---- Middle East / Central Asia ----
    "he": {"name": "Hebrew",      "native": "עברית",             "tier": "mid"},
    "fa": {"name": "Persian",     "native": "فارسی",             "tier": "mid"},
    "ps": {"name": "Pashto",      "native": "پښتو",              "tier": "low"},
    "az": {"name": "Azerbaijani", "native": "Azerbaycan",       "tier": "low"},
    "kk": {"name": "Kazakh",      "native": "Қазақ",            "tier": "low"},
    "uz": {"name": "Uzbek",       "native": "Ozbek",            "tier": "low"},
    "ky": {"name": "Kyrgyz",      "native": "Кыргыз",           "tier": "low"},
    "tg": {"name": "Tajik",       "native": "Тоҷикӣ",           "tier": "low"},
    "mn": {"name": "Mongolian",   "native": "Монгол",           "tier": "low"},
    "ka": {"name": "Georgian",    "native": "ქართული",          "tier": "low"},
    "hy": {"name": "Armenian",    "native": "Հայերեն",          "tier": "low"},

    # ---- South Asia ----
    "bn": {"name": "Bengali",     "native": "বাংলা",             "tier": "mid"},
    "ur": {"name": "Urdu",        "native": "اردو",              "tier": "mid"},
    "pa": {"name": "Punjabi",     "native": "ਪੰਜਾਬੀ",            "tier": "mid"},
    "ta": {"name": "Tamil",       "native": "தமிழ்",             "tier": "mid"},
    "te": {"name": "Telugu",      "native": "తెలుగు",            "tier": "mid"},
    "mr": {"name": "Marathi",     "native": "मराठी",             "tier": "mid"},
    "kn": {"name": "Kannada",     "native": "ಕನ್ನಡ",             "tier": "low"},
    "ml": {"name": "Malayalam",   "native": "മലയാളം",           "tier": "low"},
    "or": {"name": "Odia",        "native": "ଓଡ଼ିଆ",              "tier": "low"},
    "ne": {"name": "Nepali",      "native": "नेपाली",            "tier": "low"},
    "si": {"name": "Sinhala",     "native": "සිංහල",            "tier": "low"},

    # ---- Southeast / East Asia ----
    "th": {"name": "Thai",        "native": "ไทย",               "tier": "mid"},
    "ms": {"name": "Malay",       "native": "Bahasa Melayu",    "tier": "mid"},
    "km": {"name": "Khmer",       "native": "ខ្មែរ",              "tier": "low"},
    "lo": {"name": "Lao",         "native": "ລາວ",               "tier": "low"},
    "my": {"name": "Burmese",     "native": "မြန်မာ",             "tier": "low"},
    "jv": {"name": "Javanese",    "native": "Basa Jawa",        "tier": "low"},
    "su": {"name": "Sundanese",   "native": "Basa Sunda",       "tier": "low"},
    "ceb": {"name": "Cebuano",    "native": "Cebuano",          "tier": "low"},

    # ---- Africa ----
    "sw": {"name": "Swahili",     "native": "Kiswahili",        "tier": "mid"},
    "am": {"name": "Amharic",     "native": "አማርኛ",             "tier": "low"},
    "ha": {"name": "Hausa",       "native": "Hausa",            "tier": "low"},
    "yo": {"name": "Yoruba",      "native": "Yoruba",           "tier": "low"},
    "ig": {"name": "Igbo",        "native": "Igbo",             "tier": "low"},
    "zu": {"name": "Zulu",        "native": "isiZulu",          "tier": "low"},
    "xh": {"name": "Xhosa",       "native": "isiXhosa",         "tier": "low"},
    "so": {"name": "Somali",      "native": "Soomaali",         "tier": "low"},
    "sn": {"name": "Shona",       "native": "chiShona",         "tier": "low"},
    "rw": {"name": "Kinyarwanda", "native": "Kinyarwanda",      "tier": "low"},
    "ny": {"name": "Chichewa",    "native": "Chichewa",         "tier": "low"},

    # ---- Other ----
    "af": {"name": "Afrikaans",   "native": "Afrikaans",        "tier": "mid"},
    "ht": {"name": "Haitian Creole", "native": "Kreyol Ayisyen","tier": "low"},
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
