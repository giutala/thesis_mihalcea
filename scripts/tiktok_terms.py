"""Search terms, text patterns, and key dates for the TikTok BNPL corpus.

Everything that defines what counts as a BNPL video, which provider it names,
what kind of post it is, or which theme cue it carries lives here so that the
methods chapter can cite one file. Patterns are regular expressions applied,
case-insensitively, to the video description, hashtags, and transcript.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from functools import cache

LOGGER = logging.getLogger(__name__)

# Candidate search terms evaluated in the pilot. The final collection uses the
# subset the analyst keeps after reviewing pilot relevance.
CANDIDATE_KEYWORDS: tuple[str, ...] = (
    "klarna",
    "scalapay",
    "heylight",
    "pagolight",
    "soisy",
    "pagodil",
    "paga in 3 rate",
    "pagare a rate",
    "pagamento a rate",
    "rate senza interessi",
    "compra ora paga dopo",
    "buy now pay later",
    "bnpl",
)
CANDIDATE_HASHTAGS: tuple[str, ...] = (
    "klarna",
    "scalapay",
    "bnpl",
    "buynowpaylater",
    "pagaarate",
    "acquistiarate",
    "pagain3rate",
)

# Final terms after the 25 October 2026 pilot (one request per term, last
# complete 30 days). Dropped: "soisy" (one off-topic video), "pagare a rate"
# and "pagamento a rate" (samples dominated by debt repayment, tax
# installments, and generic retailer financing rather than BNPL).
DROPPED_TERMS: tuple[str, ...] = ("soisy", "pagare a rate", "pagamento a rate")
FINAL_KEYWORDS: tuple[str, ...] = tuple(
    term for term in CANDIDATE_KEYWORDS if term not in DROPPED_TERMS
)
FINAL_HASHTAGS: tuple[str, ...] = CANDIDATE_HASHTAGS

COLLECTION_START = date(2024, 1, 1)
COLLECTION_END = date(2027, 1, 31)

# Directive (EU) 2023/2225 (CCD2) applies from 20 November 2026.
CCD2_APPLICATION_DATE = date(2026, 11, 20)
BLACK_FRIDAYS: tuple[date, ...] = (
    date(2024, 11, 29),
    date(2025, 11, 28),
    date(2026, 11, 27),
)

PROVIDER_PATTERNS: dict[str, str] = {
    "klarna": r"klarna",
    "scalapay": r"scala\s?pay",
    "paypal_pay_in_3": (
        r"paypal[^.\n]{0,40}\b(?:3|tre)\s?rate|paga\s?in\s?3\b.{0,20}paypal"
    ),
    "heylight": r"hey\s?light|pago\s?light",
    "soisy": r"soisy",
    "pagodil": r"pago\s?dil|cofidis",
    "amazon_installments": r"amazon[^.\n]{0,40}\brate\b",
}

GENERIC_BNPL_PATTERN = (
    r"buy\s?now,?\s?pay\s?later|\bbnpl\b|compra\s?ora,?\s?paga\s?dopo|"
    r"paga(?:re|to|ndo)?\s?in\s?(?:3|tre|4|quattro)\s?rate|"
    r"(?:pagare|pagato|pago|comprare|comprato|compro|acquist\w*)\s?a\s?rate|"
    r"rate\s?(?:senza|a\s?zero|0)\s?interessi|rateizz\w*|#pagaarate|#acquistiarate"
)

# Theme cues: lexical dictionaries measuring how often a theme is *mentioned*.
# They miss irony, negation, and on-screen content, so shares are reported as
# mention rates, not as validated theme prevalence.
CUE_PATTERNS: dict[str, str] = {
    "framing_free_easy": (
        r"senza\s?interessi|zero\s?interessi|tasso\s?zero|0\s?%|gratis|"
        r"senza\s?pensieri|comodissim|facilissim|in\s?un\s?click"
    ),
    "not_debt_small_amounts": (
        r"non\s?(?:è|e')\s?(?:un\s?)?debit|non\s?sono\s?debiti|tanto\s?sono|"
        r"solo\s?\d+\s?(?:€|euro)|pochi\s?euro|dividi|spezz"
    ),
    "tracking_practice": (
        r"promemoria|calendario|notifich|screenshot|excel|foglio|"
        r"tengo\s?traccia|segno\s?tutto|controllo\s?l'?app|budget"
    ),
    "losing_track": (
        r"non\s?(?:mi\s?)?ricordo|dimenticat|me\s?ne\s?(?:sono|ero)\s?scordat|"
        r"troppe\s?rate|accumul|sommers|non\s?so\s?pi[uù]\s?quant|"
        r"perso\s?il\s?conto|tutte\s?insieme"
    ),
    "payment_failure_fees": (
        r"insolut|ritard|\bmora\b|penal|commission|addebito\s?(?:fallit|rifiutat)|"
        r"carta\s?rifiutat|conto\s?in\s?rosso|scopert|recupero\s?crediti|"
        r"segnalat|\bcrif\b|bloccat"
    ),
    "paternalism_reaction": (
        r"boomer|predic|lezioncin|fatti\s?gli\s?affari|non\s?sono\s?stupid|"
        r"so\s?gestir|ognuno\s?fa|giudic|moralism"
    ),
    "regulation": (
        r"direttiva|regolament|normativ|banca\s?d'?italia|consumer\s?credit|"
        r"\bccd\b|tutela\s?(?:dei\s?)?consumatori|trasparenz|codacons|altroconsumo"
    ),
    "shopping_context": (
        r"black\s?friday|saldi|shein|zalando|haul|codice\s?sconto|offert|"
        r"natale|regal"
    ),
    # Mainly meaningful for comments: customer-service questions about a product.
    "purchase_enquiry": (
        r"prezz|quanto\s?cost|\binfo\b|dove\s?(?:siete|vi\s?trov|si\s?trov|l'?hai|"
        r"trov)|disponibil|spedizion|\blink\b|costa"
    ),
}

# Provider accounts are recognized from the handle only, because ordinary users
# often name a provider in their bio. Remaining rules are checked in order on
# handle and bio; the first match wins.
PROVIDER_HANDLE_PATTERN = r"klarna|scalapay|heylight|pagolight|soisy|pagodil|cofidis"
CREATOR_TYPE_RULES: tuple[tuple[str, str], ...] = (
    (
        "news_institution",
        r"\bnews\b|notizi|giornal|quotidian|redazione|magazine|\btg\b|"
        r"banca\s?d'?italia|consumatori|codacons|altroconsumo|adiconsum",
    ),
    (
        "finfluencer_educator",
        r"finanz|invest|risparm|consulent|educazione\s?finanziaria|"
        r"\betf\b|trading|crypto|money|soldi",
    ),
    (
        "merchant_brand",
        r"\bshop\b|store|negozio|boutique|spedizion|ordin[ia]|e-?commerce|showroom",
    ),
)
# Post types are checked in this order; the first match wins. Strong
# commentary vocabulary comes first because educators also quote euro
# amounts; strong shop markers (including phone numbers and TikTok Shop
# affiliate unboxings) come before the first-person rule because shop
# captions use first-person phrasing too ("da noi paghi", "la mia boutique").
COMMENTARY_PATTERN = (
    r"educazione\s?finanziaria|finanza\s?personale|credito\s?al\s?consumo|"
    r"indebit|trappola|costano\s?di\s?pi[uù]|ci\s?fanno\s?spendere|"
    r"personalfinance|indagine|non\s?(?:lo\s?)?chiami\s?debito|"
    r"(?:è|sono)\s?(?:un\s?)?debit[oi]|consigli\s?(?:di|per)\s?(?:soldi|risparmi)"
)
STRONG_AD_PATTERN = (
    r"spedizion|whatsapp|vieni\s?a\s?trovarci|negozio|\bshop\b|sito\s?web|"
    r"www\.|\.it\b|\.com\b|link\s?in\s?bio|nuovi\s?arrivi|nuova\s?collezione|"
    r"\d\s?€|€\s?\d|prezz|disponibil|\btaglie?\b|boutique|versand|livraison|"
    r"shipping|zahlung|paiement|#tiktoks?c?hop|cavalcalonda\w*risparmi|"
    r"#offerteperte|vi\s?aspettiamo|\b3\d{2}[\s.]?\d{3}[\s.]?\d{3,4}\b"
)
# "Mi è arrivato" is left out on purpose: it mostly opens affiliate unboxings.
PERSONAL_PATTERN = (
    r"\b(?:ho|avevo|abbiamo)\s(?:\w+\s){0,3}(?:pagato|comprato|preso|usato|"
    r"fatto)\b[^.]{0,60}(?:rat|klarna|scalapay|paypal)|\ble\s?mie\s?rate\b|"
    r"\bio\s?(?:pago|uso|ho\s?usato)\b|la\s?mia\s?esperienza|"
    r"\bmi\s?(?:hanno|è)\s?(?:addebitat|bloccat)|truffat"
)
WEAK_AD_PATTERN = (
    r"\bvia\s[a-z]|ordin[ai]|offert|\beuro\b|promo|acquista|preventiv|"
    r"pag(?:a|ar[e]?|amento)\s?(?:anche\s?)?con|puoi\s?pagare|"
    r"possibilit[àa]\s?di\s?pag|clicca|scopri|collezion|abbigliament|"
    r"#?tiktokshop|nuova\s?apertura|appuntament|paghi|\bcorso\s[a-z]|"
    r"\bstudio\b|finanziament|pagament|website|my\s?bio|payment"
)
POST_TYPE_RULES: tuple[tuple[str, str], ...] = (
    ("financial_commentary", COMMENTARY_PATTERN),
    ("shop_ad", STRONG_AD_PATTERN),
    ("personal_experience", PERSONAL_PATTERN),
    ("shop_ad", WEAK_AD_PATTERN),
)
POST_TYPES: tuple[str, ...] = (
    "personal_experience",
    "financial_commentary",
    "shop_ad",
    "other",
)

CREATOR_TYPES: tuple[str, ...] = (
    "provider_official",
    *(name for name, _ in CREATOR_TYPE_RULES),
    "ordinary_user",
    "unknown",
)


@cache
def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a project text pattern with the shared matching flags.

    Parameters
    ----------
    pattern : str
        Regular expression from this module.

    Returns
    -------
    re.Pattern of str
        Case-insensitive, Unicode-aware compiled expression.

    Raises
    ------
    re.error
        If the expression is invalid.

    Notes
    -----
    Keeping one flag set avoids accidental case-sensitive matches in analysis.
    """
    return re.compile(pattern, re.IGNORECASE)


def mentioned_providers(text: str) -> list[str]:
    """Return the BNPL providers named in a text, in configuration order.

    Parameters
    ----------
    text : str
        Combined description, hashtags, and transcript of one video or comment.

    Returns
    -------
    list of str
        Provider keys from ``PROVIDER_PATTERNS``; empty when none match.

    Raises
    ------
    None

    Notes
    -----
    PayPal and Amazon are only counted when installments are named nearby,
    because both brands appear in many non-BNPL videos.
    """
    return [
        name
        for name, pattern in PROVIDER_PATTERNS.items()
        if compile_pattern(pattern).search(text)
    ]


def is_bnpl_relevant(text: str) -> bool:
    """Return whether a text names a BNPL provider or a generic BNPL phrase.

    Parameters
    ----------
    text : str
        Combined description, hashtags, and transcript.

    Returns
    -------
    bool
        True when at least one provider or generic installment pattern matches.

    Raises
    ------
    None

    Notes
    -----
    This rule removes off-topic API matches. Generic installment phrases are
    kept but reported separately from named providers via ``bnpl_signal``.
    """
    return bool(mentioned_providers(text)) or bool(
        compile_pattern(GENERIC_BNPL_PATTERN).search(text)
    )


def classify_creator(username: str, bio: str, user_found: bool) -> str:
    """Assign a rule-based creator type from a username and profile bio.

    Parameters
    ----------
    username : str
        TikTok handle of the video author.
    bio : str
        Public profile description; empty when unavailable.
    user_found : bool
        Whether the user-info endpoint returned a profile.

    Returns
    -------
    str
        One of ``CREATOR_TYPES``.

    Raises
    ------
    None

    Notes
    -----
    Labels are approximate: bios are short and many shops have no bio, so
    ``post_type`` is the primary content classification.
    """
    if not user_found:
        return "unknown"
    if compile_pattern(PROVIDER_HANDLE_PATTERN).search(username):
        return "provider_official"
    text = f"{username} {bio}"
    for creator_type, pattern in CREATOR_TYPE_RULES:
        if compile_pattern(pattern).search(text):
            return creator_type
    return "ordinary_user"


@cache
def bnpl_signal(text: str) -> str:
    """Return how explicitly a text refers to BNPL.

    Parameters
    ----------
    text : str
        Combined description, hashtags, and transcript.

    Returns
    -------
    str
        ``named_provider`` when a provider is named, ``bnpl_phrase`` for a
        generic BNPL phrase only, otherwise ``none``.

    Raises
    ------
    None

    Notes
    -----
    Separating the two keeps generic installment offers from inflating
    provider-specific counts.
    """
    if mentioned_providers(text):
        return "named_provider"
    if compile_pattern(GENERIC_BNPL_PATTERN).search(text):
        return "bnpl_phrase"
    return "none"


@cache
def classify_post(text: str) -> str:
    """Assign a rule-based post type from the text of a video.

    Parameters
    ----------
    text : str
        Combined description, hashtags, and transcript.

    Returns
    -------
    str
        One of ``POST_TYPES``.

    Raises
    ------
    None

    Notes
    -----
    The pilot showed that most results are shop and service ads that list
    BNPL as a payment option, so separating them from commentary and personal
    accounts is the first step of every content analysis.
    """
    for post_type, pattern in POST_TYPE_RULES:
        if compile_pattern(pattern).search(text):
            return post_type
    return "other"
