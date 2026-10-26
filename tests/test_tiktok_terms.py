"""Checks for the BNPL relevance, provider, post-type, and creator rules."""

from __future__ import annotations

from scripts.tiktok_terms import (
    bnpl_signal,
    classify_creator,
    classify_post,
    is_bnpl_relevant,
    mentioned_providers,
)


def test_relevance_and_provider_rules() -> None:
    assert mentioned_providers("Ho pagato con Scalapay e Klarna") == [
        "klarna",
        "scalapay",
    ]
    assert mentioned_providers("pagato con paypal in 3 rate") == ["paypal_pay_in_3"]
    assert mentioned_providers("pagato con paypal") == []
    assert is_bnpl_relevant("Comprato a rate senza interessi")
    assert not is_bnpl_relevant("Le rate del mutuo")


def test_creator_rules_use_handle_for_provider_accounts() -> None:
    assert classify_creator("scalapay_it", "", True) == "provider_official"
    assert classify_creator("giulia", "Uso klarna per tutto", True) == "ordinary_user"
    assert classify_creator("money.tips", "Educazione finanziaria", True) == (
        "finfluencer_educator"
    )
    assert classify_creator("anyone", "", False) == "unknown"


def test_bnpl_signal_separates_named_providers_from_phrases() -> None:
    assert bnpl_signal("Paga con Klarna") == "named_provider"
    assert bnpl_signal("Compra ora, paga dopo") == "bnpl_phrase"
    assert bnpl_signal("Ricetta della pasta") == "none"


def test_post_types_check_shop_markers_before_first_person() -> None:
    assert classify_post("Il BNPL è credito al consumo, attenzione") == (
        "financial_commentary"
    )
    assert classify_post("Ho pagato con Klarna, spedizioni in 24h") == "shop_ad"
    assert classify_post("Ho pagato con Klarna e me ne pento") == (
        "personal_experience"
    )
    assert classify_post("Paga con Scalapay") == "shop_ad"
    assert classify_post("#klarna #perte") == "other"
