# -*- coding: utf-8 -*-
"""config_loader.get_secret env guvenligi — string normalize + tek-harf sizintisi yok.

UC SORU (CLAUDE.md section 9):
1. Kim cagiriyor? notify._topic/_telegram_ayari + tum gelecek cagiranlar.
2. Hangi gorevden? saatlik auto_process (bildirim yolu).
3. Calismadigini nasil anlariz? Bu test FAIL.

Olay (2026-10-08): notify string env adi geciyordu; get_secret onu HARF HARF
dondu ve `_` env degiskeni (python yolu) eslesince chat_id yerine python yolu
dondu -> Telegram `chat not found`, tum uyarilar cop oldu. Ayni bug ntfy
topic'ini de bozuyordu (cift kanal olumu).
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def test_string_env_listeye_cevrili():
    from tools.config_loader import get_secret
    os.environ["FMS_TEST_VAR_XQZ"] = "dogru-deger"
    try:
        # string gecilse bile tek isim olarak aranmali
        assert get_secret("yok.boyle", "FMS_TEST_VAR_XQZ") == "dogru-deger"
    finally:
        del os.environ["FMS_TEST_VAR_XQZ"]


def test_tek_harf_env_calnamaz():
    from tools.config_loader import get_secret
    # `_` env'i varsa bile (Windows launcher koyar), string adin harfleri eslesmemeli
    assert "_" in os.environ, "bu test `_` env'ini gerektirir"
    assert get_secret("yok.boyle.anahtar", "ASLA_VAROLMAYAN_UZUN_AD_QWX") is None


def test_notify_chat_id_envden_okunur():
    import notify
    eski_sirlar, eski_cfg = notify._telegram_sirlari, notify._yapilandirma
    try:
        notify._telegram_sirlari = lambda: {"bot_token": "T" * 30, "chat_id": "-1001"}
        notify._yapilandirma = lambda: {}
        os.environ["NOTIFY_TELEGRAM_CHAT_ID"] = "5519122845"
        try:
            token, chat, engel = notify._telegram_ayari()
        finally:
            del os.environ["NOTIFY_TELEGRAM_CHAT_ID"]
        assert engel is None, engel
        assert chat == "5519122845", chat  # python yolu DEGIL
        assert "Python" not in str(chat) and "/" not in str(chat)
    finally:
        notify._telegram_sirlari, notify._yapilandirma = eski_sirlar, eski_cfg


def test_ntfy_topic_envden_okunur():
    import notify
    eski_cfg = notify._yapilandirma
    try:
        notify._yapilandirma = lambda: {}
        os.environ["NTFY_TOPIC"] = "fms-test-topic-123"
        try:
            assert notify._topic() == "fms-test-topic-123", notify._topic()
        finally:
            del os.environ["NTFY_TOPIC"]
    finally:
        notify._yapilandirma = eski_cfg
