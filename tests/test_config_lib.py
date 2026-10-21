"""Tests for config_lib modules."""

import os
import sys
import tempfile
import pytest

# Ensure repo root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set env var before importing config_lib
os.environ.setdefault("FMS_SECRETS_KEY", "test-key-123456789012")

from config_lib import (
    DashboardMetricsCollector,
    SecretsManager, get_secrets_manager, get_secret,
    StateManager, get_state_manager,
    PerformanceMonitor, MetricsCollector, AlertManager, get_monitor, record_metric, alert_if,
    TaskQueue, get_queue, task,
    BackupManager, get_backup_manager,
    Environment, get_env, is_production, is_development, is_debug, is_feature_enabled,
    FeatureFlags, get_feature_flags, is_enabled,
    APIDocumentation, create_fms_api_docs,
    Dashboard, get_dashboard,
    MLAnalytics, get_ml_analytics, predict_performance, predict_revenue, suggest_upload_time,
    LoadTester, get_load_tester, LoadTestResult, TestType, FailureType,
    MobileAppConfig, get_mobile_config, create_mobile_app_structure,
)


# ============== Environment Tests ==============

class TestEnvironment:
    def test_get_env(self):
        env = get_env()
        assert env is not None
        assert env.type.value in ("development", "staging", "production")

    def test_is_development(self):
        assert is_development() in (True, False)  # depends on ENV var

    def test_is_debug(self):
        env = get_env()
        # In development env, debug should be True
        if env.type.value == "development":
            assert env.is_debug() == True
        assert isinstance(env.is_debug(), bool)

    def test_is_production(self):
        assert isinstance(is_production(), bool)

    def test_is_feature_enabled(self):
        # advanced_analytics is enabled by default
        assert is_feature_enabled("advanced_analytics") == True

    def test_get_api_endpoint(self):
        env = get_env()
        endpoint = env.get_api_endpoint("database")
        assert isinstance(endpoint, str)

    def test_get_config(self):
        env = get_env()
        config = env.get_config()
        assert config is not None
        assert config.name == env.type.value

    def test_switch_environment(self):
        env = get_env()
        original = env.type.value
        from config_lib.environment import EnvironmentType
        env.switch_environment(EnvironmentType.STAGING)
        assert env.type.value == "staging"
        # Switch back
        env.switch_environment(EnvironmentType(original))


# ============== Feature Flags Tests ==============

class TestFeatureFlags:
    def test_is_enabled_disabled_by_default(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            assert ff.is_enabled("new_caption_algorithm") == False
        finally:
            os.unlink(f.name)

    def test_is_enabled_globally_enabled(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            assert ff.is_enabled("advanced_analytics") == True
        finally:
            os.unlink(f.name)

    def test_enable(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            ff.enable("new_caption_algorithm", user_id="test_user")
            assert ff.is_enabled("new_caption_algorithm") == True
        finally:
            os.unlink(f.name)

    def test_disable(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            ff.disable("advanced_analytics", user_id="test_user")
            assert ff.is_enabled("advanced_analytics") == False
            ff.enable("advanced_analytics", user_id="test_user")
        finally:
            os.unlink(f.name)

    def test_kill_switch(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            ff.enable("new_caption_algorithm", user_id="test_user")
            ff.kill("new_caption_algorithm", user_id="test_user")
            assert ff.is_enabled("new_caption_algorithm") == False
            ff.un_kill("new_caption_algorithm", user_id="test_user")
            assert ff.is_enabled("new_caption_algorithm") == True
        finally:
            os.unlink(f.name)

    def test_set_rollout_percentage(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            ff.enable("new_caption_algorithm", user_id="test_user")
            ff.set_rollout_percentage("new_caption_algorithm", 50, user_id="test_user")
            assert ff.flags["new_caption_algorithm"].rollout_percentage == 50
        finally:
            os.unlink(f.name)

    def test_add_remove_user(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            ff = FeatureFlags(config_path=f.name)
        try:
            ff.enable("experimental_features", user_id="test_user")
            ff.add_user("experimental_features", "test_user")
            assert ff.is_enabled("experimental_features", user_id="test_user") == True
            # Remove user - falls back to percentage rollout (100%) so still enabled
            ff.remove_user("experimental_features", "test_user")
            assert ff.is_enabled("experimental_features", user_id="test_user") == True
            # Disable to truly turn off
            ff.disable("experimental_features", user_id="test_user")
            assert ff.is_enabled("experimental_features", user_id="test_user") == False
        finally:
            os.unlink(f.name)

    def test_is_enabled_wrapper(self):
        result = is_enabled("advanced_analytics")
        assert isinstance(result, bool)

    def test_get_flag(self):
        ff = get_feature_flags()
        flag = ff.get_flag("advanced_analytics")
        assert flag is not None
        assert flag.name == "advanced_analytics"

    def test_list_flags(self):
        ff = get_feature_flags()
        flags = ff.list_flags()
        assert len(flags) > 0
        assert all("name" in f for f in flags)

    def test_get_audit_log(self):
        ff = get_feature_flags()
        ff.is_enabled("advanced_analytics")
        log = ff.get_audit_log("advanced_analytics")
        assert len(log) > 0
        assert log[0]["feature"] == "advanced_analytics"

    def test_get_metrics(self):
        ff = get_feature_flags()
        metrics = ff.get_metrics("advanced_analytics")
        assert "enabled_count" in metrics


# ============== API Docs Tests ==============

class TestAPIDocs:
    def test_create_docs(self):
        docs = create_fms_api_docs()
        assert docs is not None
        assert docs.title == "Famous Music Studio API"

    def test_endpoint_count(self):
        docs = create_fms_api_docs()
        assert len(docs.endpoints) > 0

    def test_generate_json(self):
        docs = create_fms_api_docs()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = docs.generate_json(f.name)
        assert os.path.isfile(path)
        os.unlink(path)

    def test_generate_html(self):
        docs = create_fms_api_docs()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = docs.generate_html(f.name)
        assert os.path.isfile(path)
        os.unlink(path)

    def test_generate_all(self):
        docs = create_fms_api_docs()
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "swagger.json")
            html_path = os.path.join(tmpdir, "swagger.html")
            docs.generate_json(json_path)
            docs.generate_html(html_path)
            assert os.path.isfile(json_path)
            assert os.path.isfile(html_path)


# ============== Dashboard Tests ==============

class TestDashboard:
    def setup_method(self):
        # Clean global dashboard state before each test
        db = get_dashboard()
        db.reset()

    def test_get_dashboard(self):
        db = get_dashboard()
        assert db is not None

    def test_record_metric(self):
        db = get_dashboard()
        db.record_metric("test_metric", 42.0)
        value = db.get_metric("test_metric")
        assert value is not None

    def test_get_dashboard_data(self):
        db = get_dashboard()
        db.record_metric("test_metric", 42.0)
        data = db.get_dashboard_data()
        assert "metrics" in data
        assert "timestamp" in data

    def test_metrics_collector(self):
        db = get_dashboard()
        db.record_metric("test_metric", 10.0)
        metrics = db.collector.get_metrics("test_metric")
        assert len(metrics) == 1
        assert metrics[0].value == 10.0
        # Clean up
        db.collector.metrics.clear()

    def test_aggregate_avg(self):
        db = get_dashboard()
        db.record_metric("test_metric", 10.0)
        db.record_metric("test_metric", 20.0)
        avg = db.collector.get_aggregate("test_metric", "avg")
        assert avg == 15.0
        db.collector.metrics.clear()

    def test_aggregate_p95(self):
        db = get_dashboard()
        for i in range(100):
            db.record_metric("test_metric", float(i))
        p95 = db.collector.get_aggregate("test_metric", "p95")
        assert p95 is not None
        assert p95 >= 90  # Should be around 95

    @pytest.mark.slow
    def test_prometheus_export(self):
        db = get_dashboard()
        db.record_metric("test_metric", 42.0)
        # Dashboard server has prometheus exporter built-in
        exporter = db.server.prometheus_exporter
        output = exporter.export()
        assert "test_metric" in output
        assert "42.0" in output


# ============== ML Analytics Tests ==============

class TestMLAnalytics:
    def test_predict_performance(self):
        ml = get_ml_analytics()
        pred = ml.predict_performance({"theme": "pop", "title": "Test Song"})
        assert pred.value > 0
        assert 0 <= pred.confidence <= 1
        assert pred.type.value == "performance"

    def test_predict_revenue(self):
        ml = get_ml_analytics()
        pred = ml.predict_revenue({"platform": "youtube"}, views_prediction=10000)
        assert pred.value >= 0
        assert pred.type.value == "revenue"

    def test_suggest_upload_time(self):
        ml = get_ml_analytics()
        pred = ml.suggest_optimal_upload_time({"platform": "tiktok"})
        assert pred.type.value == "optimal_time"
        assert pred.confidence > 0

    def test_analyze_trends_upward(self):
        ml = get_ml_analytics()
        data = [{"views": 100}, {"views": 120}, {"views": 150}, {"views": 200}]
        result = ml.analyze_trends(data)
        assert result["trend"] == "upward"
        assert result["growth_rate"] > 0

    def test_analyze_trends_downward(self):
        ml = get_ml_analytics()
        data = [{"views": 200}, {"views": 150}, {"views": 100}, {"views": 50}]
        result = ml.analyze_trends(data)
        assert result["trend"] == "downward"

    def test_analyze_trends_stable(self):
        ml = get_ml_analytics()
        data = [{"views": 100}, {"views": 105}, {"views": 98}, {"views": 102}]
        result = ml.analyze_trends(data)
        assert result["trend"] == "stable"

    def test_train_model(self):
        ml = get_ml_analytics()
        training_data = [
            {"views": 100, "theme": "pop", "title": "A"},
            {"views": 200, "theme": "rock", "title": "B"},
            {"views": 150, "theme": "pop", "title": "C"},
            {"views": 300, "theme": "rock", "title": "D"},
            {"views": 250, "theme": "pop", "title": "E"},
        ]
        result = ml.train_model(training_data)
        assert result == True

    def test_get_recommendations(self):
        ml = get_ml_analytics()
        metadata = {"title": "A", "hashtags": [], "upload_time": "12:00"}
        recs = ml.get_recommendations(metadata)
        assert len(recs) > 0
        assert any(r["type"] == "title_length" for r in recs)
        assert any(r["type"] == "hashtags" for r in recs)


# ============== Load Tester Tests ==============

class TestLoadTester:
    def test_get_load_tester(self):
        lt = get_load_tester()
        assert lt is not None
        assert len(lt.chaos_scenarios) == 4

    @pytest.mark.slow
    def test_run_load_test(self):
        lt = get_load_tester()
        result = lt.run_load_test("/test", concurrent_users=2, duration_seconds=2, _test_mode=True)
        assert result.total_requests > 0
        assert result.duration_seconds >= 2
        assert isinstance(result.test_type, TestType)

    def test_load_test_result(self):
        lt = get_load_tester()
        result = lt.run_load_test("/test", concurrent_users=2, duration_seconds=1)
        assert result.successful_requests >= 0
        assert result.failed_requests >= 0
        assert result.error_rate >= 0
        assert result.requests_per_second >= 0

    def test_generate_report(self):
        lt = get_load_tester()
        result = lt.run_load_test("/test", concurrent_users=2, duration_seconds=1)
        report = lt.generate_report(result)
        assert "summary" in report
        assert "performance" in report
        assert "recommendations" in report

    def test_stress_test(self):
        lt = get_load_tester()
        results = lt.run_stress_test("/test", max_users=10, step_size=5, _test_mode=True)
        assert len(results) > 0
        assert all(isinstance(r, LoadTestResult) for r in results)

    def test_chaos_test(self):
        lt = get_load_tester()
        result = lt.run_chaos_test("/test", duration_seconds=2, _test_mode=True)
        assert result.test_type == TestType.CHAOS
        assert result.total_requests > 0


# ============== Mobile App Tests ==============

class TestMobileApp:
    def test_get_mobile_config(self):
        mc = get_mobile_config()
        assert mc is not None
        assert mc.get("app_name") == "Famous Music Studio"

    def test_mobile_config_get_set(self):
        mc = get_mobile_config()
        mc.set("test_key", "test_value")
        assert mc.get("test_key") == "test_value"

    def test_mobile_config_is_feature_enabled(self):
        mc = get_mobile_config()
        assert mc.is_feature_enabled("upload") == True
        assert mc.is_feature_enabled("nonexistent") == False

    def test_mobile_config_get_api_url(self):
        mc = get_mobile_config()
        url = mc.get("api_base_url")
        assert isinstance(url, str)
        assert "api/v1" in url

    def test_mobile_config_theme(self):
        mc = get_mobile_config()
        theme = mc.get("theme")
        assert "primary_color" in theme
        assert "secondary_color" in theme

    def test_create_mobile_app_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_mobile_app_structure(tmpdir)
            assert len(result["files"]) > 0
            assert len(result["directories"]) > 0
            # Verify key files exist
            files = result["files"]
            assert any("LoginScreen.js" in f for f in files)
            assert any("DashboardScreen.js" in f for f in files)
            assert any("package.json" in f for f in files)
            assert any("App.js" in f for f in files)

    def test_mobile_config_save(self):
        mc = get_mobile_config()
        mc.set("test_save", "value123")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            mc.config_path = f.name
            result = mc.save_config()
        assert result == True
        # Verify file was written
        assert os.path.isfile(f.name)
        import json
        with open(f.name) as f:
            data = json.load(f)
        assert data.get("test_save") == "value123"
        os.unlink(f.name)


# ============== Integration Tests ==============

class TestIntegration:
    def test_all_modules_importable(self):
        """Verify all 12 modules can be imported from config_lib."""
        import config_lib
        for name in config_lib.__all__:
            assert hasattr(config_lib, name), f"Missing export: {name}"
        # Verify LoadTestResult is importable
        from config_lib import LoadTestResult
        assert LoadTestResult is not None

    def test_feature_flags_with_environment(self):
        """Feature flags work with environment context."""
        env = get_env()
        ff = get_feature_flags()
        # Should not crash with environment context
        result = ff.is_enabled("advanced_analytics", context={"env": env.type.value})
        assert isinstance(result, bool)

    def test_dashboard_with_metrics(self):
        """Dashboard records and retrieves metrics."""
        db = get_dashboard()
        db.record_metric("upload_duration", 12.5)
        db.record_metric("upload_duration", 15.0)
        avg = db.get_metric("upload_duration")
        assert avg is not None
        assert 12.5 <= avg <= 15.0

    def test_ml_with_environment(self):
        """ML analytics works with environment metadata."""
        ml = get_ml_analytics()
        env = get_env()
        pred = ml.predict_performance({
            "theme": "pop",
            "language": "tr",
            "env": env.type.value
        })
        assert pred.value > 0
