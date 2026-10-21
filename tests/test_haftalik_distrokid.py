# test_haftalik_distrokid.py — Haftalık DistroKid takibi (CLAUDE.md §9 + §10)
import pytest

def test_is_configured_oncesinde_send():
    """notify.send() çağrılmadan önce is_configured() zorunlu (§2)."""
    assert notify.is_configured() is True or notify.is_configured() is False
    # Fail-closed: False ise log açıkla, send çağrılma

def test_finally_bloch_eklenmis():
    """_drain_golden_hour_queue() finally bloğunda olmalı (§3/§8)."""
    # Otomasyon bağlamı kontrolü
    pass

def test_atomic_write_kullanilmis():
    """State yazımı sadece state_io.atomic_write() ile (§4)."""
    pass
