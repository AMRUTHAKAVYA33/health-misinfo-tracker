import re

HASHTAG_PATTERN = re.compile(r"#\w+")

def extract_hashtags(text: str):
    return HASHTAG_PATTERN.findall(text or "")

NEGATION_KEYWORDS = [
    "no scientific evidence",
    "has debunked this myth",
    "debunked this myth",
    "myth has been debunked",
    "myth",
    "fact check",
    "false claim",
    "not true",
    "is incorrect",
    "is false",
]

MISINFO_KEYWORDS = [
    "5g",
    "coronavirus",
    "covid",
    "covid-19",
    "vaccine",
    "vaccines",
    "covid19",
]


def is_explicit_debunk(text: str) -> bool:
    """
    Heuristic: if sentence clearly says there is no evidence / myth debunked
    about COVID/5G/vaccines, treat it as real even if model says fake.
    """
    if not text:
        return False
    t = text.lower()
    return any(nk in t for nk in NEGATION_KEYWORDS) and any(
        mk in t for mk in MISINFO_KEYWORDS
    )
