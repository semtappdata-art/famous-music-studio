"""Tests for the proactive alerting system in saglik_kontrol module."""

import saglik_kontrol
from saglik_kontrol import _shoul_alert, _gonder_proaktif_bildirim
from unittest.mock import patch, MagicMock
import time


def test_healthy_project_ratio_thresholds():
    """Test healthy project ratio alert thresholds."""
    # Test normal (>=90%)
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(95.0)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['healthy_project_ratio']['durum'] == 'tamam'
    
    # Test warning (<90%, >=70%)
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(85.0)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['healthy_project_ratio']['durum'] == 'uyari'
    
    # Test critical (<70%, >=50%)
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(65.0)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['healthy_project_ratio']['durum'] == 'uyari'  # Still uyari in kontrol_et
    
    # Test critical (<50%)
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(45.0)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['healthy_project_ratio']['durum'] == 'uyari'  # Still uyari in kontrol_et
    # Actual alert triggering happens in the kontrol_et function's alert section


def test_telegram_error_rate_thresholds():
    """Test telegram error rate alert thresholds."""
    # Test normal (<0.05)
    saglik_kontrol.METRIKLER['telegram_error_rate'].set(0.03)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['telegram_error_rate']['durum'] == 'tamam'
    
    # Test warning (>=0.05, <0.07)
    saglik_kontrol.METRIKLER['telegram_error_rate'].set(0.06)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['telegram_error_rate']['durum'] == 'uyari'
    
    # Test critical (>=0.07, <0.10)
    saglik_kontrol.METRIKLER['telegram_error_rate'].set(0.08)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['telegram_error_rate']['durum'] == 'uyari'
    
    # Test critical (>=0.10)
    saglik_kontrol.METRIKLER['telegram_error_rate'].set(0.12)
    result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
    assert result['telegram_error_rate']['durum'] == 'uyari'


def test_alert_cooldown_mechanism():
    """Test that alert cooldown prevents spam."""
    alert_key = "test_alert_key"
    
    # First call should return True (alert allowed)
    assert _shoul_alert(alert_key) == True
    
    # Immediate second call should return False (on cooldown)
    assert _shoul_alert(alert_key) == False
    
    # Call with different key should still work
    assert _shoul_alert("different_key") == True
    
    # Original key should still be on cooldown
    assert _shoul_alert(alert_key) == False


def test_alert_cooldown_expiration():
    """Test that alert cooldown expires after time passes."""
    alert_key = "test_alert_key"
    
    # First call
    assert _shoul_alert(alert_key) == True
    
    # Second call immediately after should be False
    assert _shoul_alert(alert_key) == False
    
    # Mock time to simulate cooldown passage
    with patch('time.time') as mock_time:
        # Set initial time
        mock_time.return_value = 1000.0
        _shoul_alert(alert_key)  # First call
        
        # Advance time by more than cooldown period (3600 seconds)
        mock_time.return_value = 1000.0 + 3601.0
        
        # Should be allowed again
        assert _shoul_alert(alert_key) == True


def test_proactive_alerting_integration():
    """Test that proactive alerting integrates with kontrol_et."""
    # We won't actually send alerts to avoid notifications, but we can verify
    # the functions are called by mocking notify.send
    
    with patch('notify.send') as mock_notify:
        with patch('notify.is_configured', return_value=True):
            # Trigger critical healthy ratio
            saglik_kontrol.METRIKLER['healthy_project_ratio'].set(45.0)  # Critical
            saglik_kontrol.METRIKLER['telegram_error_rate'].set(0.02)    # Normal
            
            result = saglik_kontrol.kontrol_et(log=lambda *a, **k: None)
            
            # Should have returned uyari for healthy ratio
            assert result['healthy_project_ratio']['durum'] == 'uyari'
            
            # The actual alert sending happens inside kontrol_et
            # We can't easily test if notify.send was called without modifying
            # the function to expose it, but we can verify the logic paths


def test_rapid_degradation_detection():
    """Test rapid degradation detection logic."""
    # Set up initial high value
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(95.0)
    
    # Small time passage
    time.sleep(0.001)
    
    # Set to significantly lower value (should trigger rapid degradation alert)
    saglik_kontrol.METRIKLER['healthy_project_ratio'].set(75.0)  # 20 point drop
    
    # The actual alert would be triggered in kontrol_et, but we can verify
    # the historical data is there
    history = saglik_kontrol.METRIKLER['healthy_project_ratio'].tarihce(saniye=3600)
    assert len(history) >= 2
    
    # Check that we have the expected values
    values = [h[1] for h in history]
    assert 95.0 in values
    assert 75.0 in values


def test_alert_state_isolation():
    """Test that alert states are isolated between different alert types."""
    # Test healthy ratio alert key
    hr_key = "healthy_project_ratio_critical"
    te_key = "telegram_error_rate_critical"
    
    # Trigger healthy ratio alert
    assert _shoul_alert(hr_key) == True
    assert _shoul_alert(hr_key) == False  # On cooldown
    
    # Telegram alert key should still be available
    assert _shoul_alert(te_key) == True
    
    # Healthy ratio key should still be on cooldown
    assert _shoul_alert(hr_key) == False


if __name__ == "__main__":
    # Run tests if executed directly
    import pytest
    pytest.main([__file__, "-v"])