"""
Professional Policy Monitoring System for Famous Music Studio
============================================================

This module provides enterprise-grade policy monitoring and compliance
management for multi-platform content distribution.

Features:
- Real-time policy change detection from platform sources
- Automated content compliance scanning
- Risk assessment and scoring
- Alerting and notification system
- Historical trend analysis
- Extensible architecture for new platforms
- Comprehensive logging and audit trails
- Configuration-driven policy rules

Usage:
    python -m upload.policy_monitor --mode monitor --interval 3600
    python -m upload.policy_monitor --mode scan --project "projects/song-name"
    python -m upload.policy_monitor --mode report --format json
    python -m upload.policy_monitor --mode update --force
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io
from uyumluluk import KOK_ADLARI, _KOK
from tools.json_logger import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_KOK, 'logs', 'policy_monitor.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = get_logger('policy_monitor')

# Constants
POLICY_CACHE_DIR = os.path.join(_KOK, 'policy_cache')
POLICY_STATE_FILE = os.path.join(POLICY_CACHE_DIR, 'policy_state.json')
COMPLIANCE_RESULTS_FILE = os.path.join(POLICY_CACHE_DIR, 'compliance_results.json')
ALERT_HISTORY_FILE = os.path.join(POLICY_CACHE_DIR, 'alert_history.json')
CONFIG_FILE = os.path.join(_KOK, 'config', 'policy_config.json')

# Ensure directories exist
os.makedirs(POLICY_CACHE_DIR, exist_ok=True)
os.makedirs(os.path.join(_KOK, 'logs'), exist_ok=True)
os.makedirs(os.path.join(_KOK, 'config'), exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "monitoring": {
        "enabled": True,
        "check_interval_seconds": 3600,  # 1 hour
        "platforms": ["youtube", "instagram", "tiktok", "facebook", "twitter", "bluesky", "telegram"],
        "content_scan_interval_seconds": 7200,  # 2 hours
        "max_concurrent_scans": 5
    },
    "alerting": {
        "enabled": True,
        "email_enabled": False,
        "webhook_enabled": False,
        "log_only": True,
        "alert_cooldown_minutes": 60
    },
    "risk_thresholds": {
        "low": 30,
        "medium": 60,
        "high": 80
    },
    "cpm_rates": {
        "youtube": {
            "default": 1.50,
            "by_region": {
                "US": 3.50,
                "CA": 2.80,
                "UK": 2.50,
                "AU": 2.20,
                "DE": 2.00,
                "TR": 0.80
            },
            "by_season": {
                "Q1": 1.20,   # Jan-Mar
                "Q2": 1.40,   # Apr-Jun
                "Q3": 1.80,   # Jul-Sep
                "Q4": 2.20    # Oct-Dec
            }
        }
    }
}

class PolicyViolationType(Enum):
    CONTENT_LENGTH = "content_length"
    HASHTAG_COUNT = "hashtag_count"
    MISSING_DISCLOSURE = "missing_disclosure"
    PROHIBITED_CONTENT = "prohibited_content"
    COPYRIGHT_RISK = "copyright_risk"
    AI_DISCLOSURE = "ai_disclosure"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PolicyViolation:
    """Represents a policy violation found during compliance scanning."""
    platform: str
    violation_type: PolicyViolationType
    risk_level: RiskLevel
    description: str
    current_value: Any
    limit_value: Any
    project_path: str
    timestamp: str
    remediation_suggestion: str
    policy_reference: str

@dataclass
class PolicyUpdate:
    """Represents a detected policy update from a platform."""
    platform: str
    policy_area: str
    old_value: Any
    new_value: Any
    change_type: str  # "increased", "decreased", "added", "removed"
    effective_date: str
    source_url: str
    confidence: float  # 0.0 to 1.0
    detected_at: str

class PolicyConfigManager:
    """Manages policy configuration and rules."""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_config()
        self.platform_policies = self._initialize_platform_policies()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load policy config: {e}. Using defaults.")
                return DEFAULT_CONFIG.copy()
        else:
            logger.info("Creating default policy configuration")
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save policy config: {e}")
    
    def _initialize_platform_policies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize platform-specific policy rules."""
        # Base policies - in a real implementation, these would be fetched from platforms
        base_policies = {
            "youtube": {
                "max_title_length": 100,
                "max_description_length": 5000,
                "max_tags": 30,
                "max_tag_length": 30,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "harassment", 
                    "misinformation", "copyright infringement"
                ],
                "required_disclosures": [
                    "synthetic_media", "paid_promotion", "political_content"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "youtube_terms_of_service"
            },
            "instagram": {
                "max_caption_length": 2200,
                "max_hashtags": 30,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "nudity", 
                    "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "paid_partnership", "synthetic_media"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "instagram_community_guidelines"
            },
            "tiktok": {
                "max_caption_length": 150,
                "max_hashtags": 100,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "dangerous_acts",
                    "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "synthetic_media", "paid_content"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "tiktok_community_guidelines"
            },
            "facebook": {
                "max_description_length": 63206,
                "max_hashtags": 30,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "nudity",
                    "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "paid_partnership", "synthetic_media", "political_content"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "facebook_community_standards"
            },
            "twitter": {
                "max_caption_length": 280,
                "max_hashtags": 10,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "paid_partnership", "synthetic_media"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "twitter_rules"
            },
            "bluesky": {
                "max_caption_length": 300,
                "max_hashtags": 10,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "paid_partnership", "synthetic_media"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "bluesky_community guidelines"
            },
            "telegram": {
                "max_caption_length": 1024,
                "max_hashtags": 10,
                "prohibited_content_keywords": [
                    "hate speech", "violence", "illegal_activity", "misinformation"
                ],
                "required_disclosures": [
                    "synthetic_media"
                ],
                "last_updated": None,
                "version": "1.0",
                "source": "telegram_tos"
            }
        }
        
        # Apply any custom overrides from config
        custom_overrides = self.config.get("platform_overrides", {})
        for platform, overrides in custom_overrides.items():
            if platform in base_policies:
                base_policies[platform].update(overrides)
        
        return base_policies
    
    def get_platform_policy(self, platform: str) -> Dict[str, Any]:
        """Get policy rules for a specific platform."""
        return self.platform_policies.get(platform, {})
    
    def update_platform_policy(self, platform: str, updates: Dict[str, Any]) -> bool:
        """Update policy rules for a platform."""
        if platform not in self.platform_policies:
            logger.warning(f"Unknown platform: {platform}")
            return False
        
        try:
            self.platform_policies[platform].update(updates)
            self.platform_policies[platform]["last_updated"] = datetime.now().isoformat()
            # Increment version
            current_version = self.platform_policies[platform].get("version", "1.0")
            try:
                major, minor = map(int, current_version.split("."))
                minor += 1
                if minor >= 10:
                    major += 1
                    minor = 0
                new_version = f"{major}.{minor}"
                self.platform_policies[platform]["version"] = new_version
            except ValueError:
                self.platform_policies[platform]["version"] = "1.1"
            
            logger.info(f"Updated policy for {platform} to version {self.platform_policies[platform]['version']}")
            return True
        except Exception as e:
            logger.error(f"Failed to update policy for {platform}: {e}")
            return False

class ComplianceScanner:
    """Scans content for policy violations."""
    
    def __init__(self, policy_manager: PolicyConfigManager):
        self.policy_manager = policy_manager
        self.violations_found: List[PolicyViolation] = []
    
    def scan_project_compliance(self, project_path: str) -> List[PolicyViolation]:
        """
        Scan a project for policy violations across all platforms.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            List of PolicyViolation objects found
        """
        violations = []
        
        # Load project metadata
        meta_path = os.path.join(project_path, "meta.json")
        state_path = os.path.join(project_path, "state.json")
        
        if not os.path.isfile(meta_path):
            logger.warning(f"Meta file not found: {meta_path}")
            return violations
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load meta.json for {project_path}: {e}")
            return violations
        
        state = {}
        if os.path.isfile(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load state.json for {project_path}: {e}")
        
        # Get project info
        project_name = os.path.basename(project_path)
        title = meta.get("title", "Unknown")
        
        # Scan for each platform
        platforms_to_scan = self.config["monitoring"]["platforms"]
        
        for platform in platforms_to_scan:
            platform_violations = self._scan_platform_compliance(
                platform, meta, state, project_path, project_name, title
            )
            violations.extend(platform_violations)
        
        return violations
    
    def _scan_platform_compliance(self, platform: str, meta: Dict[str, Any], 
                                state: Dict[str, Any], project_path: str,
                                project_name: str, title: str) -> List[PolicyViolation]:
        """Scan compliance for a specific platform."""
        violations = []
        policy = self.policy_manager.get_platform_policy(platform)
        
        if not policy:
            logger.warning(f"No policy found for platform: {platform}")
            return violations
        
        # Check title length
        title_length = len(title)
        max_title = policy.get("max_title_length", 100)
        if title_length > max_title:
            violations.append(PolicyViolation(
                platform=platform,
                violation_type=PolicyViolationType.CONTENT_LENGTH,
                risk_level=self._assess_risk_level(
                    title_length, max_title, PolicyViolationType.CONTENT_LENGTH
                ),
                description=f"Title exceeds maximum length for {platform}",
                current_value=title_length,
                limit_value=max_title,
                project_path=project_path,
                timestamp=datetime.now().isoformat(),
                remediation_suggestion=f"Shorten title to {max_title} characters or less",
                policy_reference=f"{platform}_title_length_limit"
            ))
        
        # Check description length (if applicable)
        description = meta.get("description", "")
        if description:
            desc_length = len(description)
            max_desc = policy.get("max_description_length", 5000)
            if desc_length > max_desc:
                violations.append(PolicyViolation(
                    platform=platform,
                    violation_type=PolicyViolationType.CONTENT_LENGTH,
                    risk_level=self._assess_risk_level(
                        desc_length, max_desc, PolicyViolationType.CONTENT_LENGTH
                    ),
                    description=f"Description exceeds maximum length for {platform}",
                    current_value=desc_length,
                    limit_value=max_desc,
                    project_path=project_path,
                    timestamp=datetime.now().isoformat(),
                    remediation_suggestion=f"Shorten description to {max_desc} characters or less",
                    policy_reference=f"{platform}_description_length_limit"
                ))
        
        # Check for AI disclosure
        ai_disclosure_given = (
            meta.get("ai_disclosure", False) or 
            state.get("ai_disclosure_added", False) or
            meta.get("ai_beiany", False)
        )
        required_disclosures = policy.get("required_disclosures", [])
        if "synthetic_media" in required_disclosures and not ai_disclosure_given:
            violations.append(PolicyViolation(
                platform=platform,
                violation_type=PolicyViolationType.AI_DISCLOSURE,
                risk_level=RiskLevel.HIGH,
                description=f"Missing required AI/synthetic media disclosure for {platform}",
                current_value=False,
                limit_value=True,
                project_path=project_path,
                timestamp=datetime.now().isoformat(),
                remediation_suggestion="Add AI disclosure: 'Bu içerik yapay zeka ile üretilmiştir'",
                policy_reference=f"{platform}_ai_disclosure_requirement"
            ))
        
        # Check for copyright risk indicators
        copyright_risk = meta.get("copyright_risk", False) or state.get("copyright_claim", False)
        if copyright_risk:
            violations.append(PolicyViolation(
                platform=platform,
                violation_type=PolicyViolationType.COPYRIGHT_RISK,
                risk_level=RiskLevel.HIGH,
                description=f"Copyright risk indicators detected for {platform}",
                current_value=True,
                limit_value=False,
                project_path=project_path,
                timestamp=datetime.now().isoformat(),
                remediation_suggestion="Review content for copyrighted material and obtain necessary licenses",
                policy_reference=f"{platform}_copyright_policy"
            ))
        
        return violations
    
    def _assess_risk_level(self, current: Any, limit: Any, 
                          violation_type: PolicyViolationType) -> RiskLevel:
        """Assess risk level based on how much a limit is exceeded."""
        if isinstance(current, (int, float)) and isinstance(limit, (int, float)):
            ratio = current / limit if limit > 0 else float('inf')
            
            if ratio >= 2.0:
                return RiskLevel.CRITICAL
            elif ratio >= 1.5:
                return RiskLevel.HIGH
            elif ratio >= 1.2:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
        
        # Default risk levels for non-quantitative violations
        risk_map = {
            PolicyViolationType.MISSING_DISCLOSURE: RiskLevel.HIGH,
            PolicyViolationType.PROHIBITED_CONTENT: RiskLevel.HIGH,
            PolicyViolationType.COPYRIGHT_RISK: RiskLevel.HIGH,
            PolicyViolationType.AI_DISCLOSURE: RiskLevel.HIGH
        }
        
        return risk_map.get(violation_type, RiskLevel.MEDIUM)

class PolicyUpdateDetector:
    """Detects policy updates from platform sources."""
    
    def __init__(self, policy_manager: PolicyConfigManager):
        self.policy_manager = policy_manager
        self.known_policies = self._load_known_policies()
    
    def _load_known_policies(self) -> Dict[str, Dict[str, Any]]:
        """Load previously known policy states."""
        if os.path.isfile(POLICY_STATE_FILE):
            try:
                with open(POLICY_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load policy state: {e}")
                return {}
        return {}
    
    def _save_known_policies(self) -> None:
        """Save current policy states for future comparison."""
        try:
            policies_to_save = {}
            for platform, policy in self.policy_manager.platform_policies.items():
                policies_to_save[platform] = {
                    "version": policy.get("version"),
                    "last_updated": policy.get("last_updated"),
                    # Save key policy values for change detection
                    "key_values": {
                        k: v for k, v in policy.items() 
                        if k in ["max_title_length", "max_description_length", 
                               "max_tags", "max_hashtags", "max_caption_length"]
                    }
                }
            
            with open(POLICY_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(policies_to_save, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save policy state: {e}")
    
    def detect_policy_updates(self) -> List[PolicyUpdate]:
        """
        Detect policy updates by comparing current policies with known states.
        
        Returns:
            List of PolicyUpdate objects representing detected changes
        """
        updates = []
        current_policies = self.policy_manager.platform_policies
        
        for platform, current_policy in current_policies.items():
            known_policy = self.known_policies.get(platform, {})
            
            if not known_policy:
                # First time seeing this platform
                logger.info(f"First-time policy load for {platform}")
                continue
            
            # Check for version changes
            current_version = current_policy.get("version", "1.0")
            known_version = known_policy.get("version", "1.0")
            
            if current_version != known_version:
                # Determine what changed by comparing key values
                current_key_values = current_policy.get("key_values", {})
                known_key_values = known_policy.get("key_values", {})
                
                all_keys = set(current_key_values.keys()) | set(known_key_values.keys())
                
                for key in all_keys:
                    old_val = known_key_values.get(key)
                    new_val = current_key_values.get(key)
                    
                    if old_val != new_val and old_val is not None and new_val is not None:
                        change_type = self._determine_change_type(key, old_val, new_val)
                        
                        updates.append(PolicyUpdate(
                            platform=platform,
                            policy_area=key,
                            old_value=old_val,
                            new_value=new_val,
                            change_type=change_type,
                            effective_date=datetime.now().isoformat(),
                            source_url=f"platform_policy_{platform}",
                            confidence=0.9,  # High confidence for direct comparison
                            detected_at=datetime.now().isoformat()
                        ))
            
            # Check for new policies added
            elif not known_policy.get("version"):  # First time seeing this platform
                logger.info(f"Initial policy load for {platform}")
        
        # Save current policies as known for next check
        self._save_known_policies()
        
        if updates:
            logger.info(f"Detected {len(updates)} policy updates")
        else:
            logger.debug("No policy updates detected")
        
        return updates
    
    def _determine_change_type(self, policy_key: str, old_val: Any, new_val: Any) -> str:
        """Determine the type of change based on policy key and values."""
        if old_val is None:
            return "added"
        if new_val is None:
            return "removed"
        
        # For numeric values, determine if increased or decreased
        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            if new_val > old_val:
                return "increased"
            elif new_val < old_val:
                return "decreased"
            else:
                return "modified"
        
        # For strings and other types
        if str(new_val) != str(old_val):
            return "modified"
        
        return "unknown"

class AlertManager:
    """Manages alerts and notifications for policy violations and updates."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_history = self._load_alert_history()
        self.alert_cooldown = {}  # Track when we last sent similar alerts
    
    def _load_alert_history(self) -> List[Dict[str, Any]]:
        """Load alert history from file."""
        if os.path.isfile(ALERT_HISTORY_FILE):
            try:
                with open(ALERT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load alert history: {e}")
                return []
        return []
    
    def _save_alert_history(self) -> None:
        """Save alert history to file."""
        try:
            # Keep only last 1000 alerts to prevent file from growing too large
            recent_alerts = self.alert_history[-1000:] if len(self.alert_history) > 1000 else self.alert_history
            with open(ALERT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(recent_alerts, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save alert history: {e}")
    
    def should_send_alert(self, alert_key: str, cooldown_minutes: int = 60) -> bool:
        """
        Check if we should send an alert based on cooldown period.
        
        Args:
            alert_key: Unique identifier for this type of alert
            cooldown_minutes: Minimum minutes between similar alerts
            
        Returns:
            True if alert should be sent, False otherwise
        """
        if not self.config["alerting"]["enabled"]:
            return False
        
        last_sent = self.alert_cooldown.get(alert_key)
        if last_sent is None:
            return True
        
        minutes_since = (datetime.now() - last_sent).total_seconds() / 60
        return minutes_since >= cooldown_minutes
    
    def send_alert(self, alert_key: str, title: str, message: str, 
                  level: str = "info") -> bool:
        """
        Send an alert through configured channels.
        
        Args:
            alert_key: Unique identifier for deduplication
            title: Alert title
            message: Alert message
            level: Alert level (info, warning, error, critical)
            
        Returns:
            True if alert was sent successfully
        """
        # Check cooldown
        if not self.should_send_alert(alert_key):
            logger.debug(f"Alert suppressed due to cooldown: {alert_key}")
            return False
        
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "key": alert_key,
            "title": title,
            "message": message,
            "level": level
        }
        
        success = False
        
        # Log alert (always enabled)
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"ALERT [{alert_key}] {title}: {message}")
        self.alert_history.append(alert_record)
        success = True
        
        # Update cooldown
        self.alert_cooldown[alert_key] = datetime.now()
        
        # Save history periodically
        if len(self.alert_history) % 10 == 0:  # Save every 10 alerts
            self._save_alert_history()
        
        # TODO: Implement other alert channels (email, webhook, etc.)
        # based on self.config["alerting"]
        
        return success

class PolicyMonitor:
    """Main policy monitoring orchestrator."""
    
    def __init__(self):
        self.config_manager = PolicyConfigManager()
        self.compliance_scanner = ComplianceScanner(self.config_manager)
        self.update_detector = PolicyUpdateDetector(self.config_manager)
        self.alert_manager = AlertManager(self.config_manager.config)
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval_seconds: int = 3600) -> None:
        """
        Start continuous policy monitoring in background thread.
        
        Args:
            interval_seconds: How often to check for policy updates
        """
        if self.running:
            logger.warning("Policy monitoring is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Started policy monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop continuous policy monitoring."""
        if not self.running:
            logger.warning("Policy monitoring is not running")
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped policy monitoring")
    
    def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        last_content_scan = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check for policy updates
                logger.debug("Checking for policy updates...")
                updates = self.update_detector.detect_policy_updates()
                
                # Send alerts for significant updates
                for update in updates:
                    if update.confidence >= 0.7:  # Only alert on high-confidence updates
                        alert_key = f"policy_update_{update.platform}_{update.policy_area}"
                        if self.alert_manager.should_send_alert(alert_key, 30):  # 30 min cooldown
                            self.alert_manager.send_alert(
                                alert_key=alert_key,
                                title=f"Policy Update: {update.platform}",
                                message=f"{update.policy_area} changed from {update.old_value} to {update.new_value}",
                                level="warning"
                            )
                
                # Scan for content compliance periodically
                if current_time - last_content_scan >= self.config_manager.config["monitoring"]["content_scan_interval_seconds"]:
                    logger.debug("Starting content compliance scan...")
                    self.scan_all_content()
                    last_content_scan = current_time
                
                # Sleep until next check
                time.sleep(min(interval_seconds, 60))  # Check at least every minute
                
            except Exception as e:
                logger.error(f"Error in policy monitoring loop: {e}")
                time.sleep(60)  # Wait a bit before retrying
    
    def scan_all_content(self) -> Dict[str, List[PolicyViolation]]:
        """
        Scan all projects for policy violations.
        
        Returns:
            Dictionary mapping project paths to lists of violations
        """
        logger.info("Starting comprehensive content compliance scan")
        all_violations = {}
        total_projects = 0
        total_violations = 0
        
        try:
            for platform_root in KOK_ADLARI:
                platform_path = os.path.join(_KOK, platform_root)
                if not os.path.isdir(platform_path):
                    continue
                
                try:
                    projects = [d for d in os.listdir(platform_path) 
                              if os.path.isdir(os.path.join(platform_path, d))]
                except OSError as e:
                    logger.warning(f"Could not list projects in {platform_path}: {e}")
                    continue
                
                for project_name in projects:
                    project_path = os.path.join(platform_path, project_name)
                    if not os.path.isdir(project_path):
                        continue
                    
                    total_projects += 1
                    violations = self.compliance_scanner.scan_project_compliance(project_path)
                    
                    if violations:
                        all_violations[project_path] = violations
                        total_violations += len(violations)
                        
                        # Send alerts for high-risk violations
                        high_risk_violations = [
                            v for v in violations 
                            if v.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                        ]
                        
                        if high_risk_violations:
                            alert_key = f"high_risk_violations_{platform_name}_{project_name}"
                            if self.alert_manager.should_send_alert(alert_key, 60):  # 60 min cooldown
                                self.alert_manager.send_alert(
                                    alert_key=alert_key,
                                    title=f"High Risk Policy Violations: {project_name}",
                                    message=f"Found {len(high_risk_violations)} high-risk violations",
                                    level="error"
                                )
            
            logger.info(f"Content scan completed: {total_projects} projects scanned, {total_violations} violations found")
            
            # Save compliance results
            self._save_compliance_results(all_violations)
            
            return all_violations
            
        except Exception as e:
            logger.error(f"Error during content compliance scan: {e}")
            return {}
    
    def scan_project(self, project_path: str) -> List[PolicyViolation]:
        """
        Scan a specific project for policy violations.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            List of PolicyViolation objects found
        """
        logger.info(f"Scanning project for compliance: {project_path}")
        violations = self.compliance_scanner.scan_project_compliance(project_path)
        logger.info(f"Scan completed: {len(violations)} violations found")
        return violations
    
    def generate_report(self, format_type: str = "text") -> str:
        """
        Generate a compliance report.
        
        Args:
            format_type: Report format ("text", "json", "csv")
            
        Returns:
            Formatted report string
        """
        logger.info(f"Generating compliance report in {format_type} format")
        
        # Load latest compliance results
        if os.path.isfile(COMPLIANCE_RESULTS_FILE):
            try:
                with open(COMPLIANCE_RESULTS_FILE, 'r', encoding='utf-8') as f:
                    compliance_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load compliance results: {e}")
                compliance_data = {}
        else:
            compliance_data = {}
        
        # Get policy update history
        policy_state = {}
        if os.path.isfile(POLICY_STATE_FILE):
            try:
                with open(POLICY_STATE_FILE, 'r', encoding='utf-8') as f:
                    policy_state = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load policy state: {e}")
        
        if format_type == "json":
            report = {
                "timestamp": datetime.now().isoformat(),
                "compliance_scan": compliance_data,
                "policy_state": policy_state,
                "alert_history_count": len(self.alert_manager.alert_history),
                "config": self.config_manager.config
            }
            return json.dumps(report, indent=2, ensure_ascii=False)
        
        elif format_type == "text":
            lines = []
            lines.append("=" * 60)
            lines.append("FAMOUS MUSIC STUDIO - POLICY COMPLIANCE REPORT")
            lines.append("=" * 60)
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            
            # Policy status
            lines.append("PLATFORM POLICY STATUS:")
            lines.append("-" * 30)
            for platform, policy in policy_state.items():
                lines.append(f"{platform.upper()}:")
                if policy:
                    for key, value in policy.items():
                        if key not in ["last_updated", "version"]:
                            lines.append(f"  {key}: {value}")
                    lines.append(f"  Version: {policy.get('version', 'Unknown')}")
                    lines.append(f"  Last Updated: {policy.get('last_updated', 'Unknown')}")
                else:
                    lines.append("  No policy data available")
                lines.append("")
            
            # Compliance summary
            if compliance_data:
                lines.append("COMPLIANCE SCAN RESULTS:")
                lines.append("-" * 30)
                total_projects = len(compliance_data)
                total_violations = sum(len(v) for v in compliance_data.values())
                lines.append(f"Projects Scanned: {total_projects}")
                lines.append(f"Total Violations: {total_violations}")
                
                if total_violations > 0:
                    lines.append("")
                    lines.append("VIOLATIONS BY PLATFORM:")
                    platform_counts = {}
                    for project_path, violations in compliance_data.items():
                        for violation in violations:
                            platform = violation.get("platform", "unknown")
                            platform_counts[platform] = platform_counts.get(platform, 0) + 1
                    
                    for platform, count in sorted(platform_counts.items()):
                        lines.append(f"  {platform.upper()}: {count} violations")
                
                lines.append("")
                lines.append("HIGH PRIORITY VIOLATIONS:")
                high_priority = []
                for project_path, violations in compliance_data.items():
                    for violation in violations:
                        if violation.get("risk_level") in ["high", "critical"]:
                            high_priority.append((project_path, violation))
                
                if high_priority:
                    for project_path, violation in high_priority[:10]:  # Show top 10
                        lines.append(f"  {os.path.basename(project_path)}: {violation.get('description')}")
                    if len(high_priority) > 10:
                        lines.append(f"  ... and {len(high_priority) - 10} more high priority violations")
                else:
                    lines.append("  No high priority violations found")
            else:
                lines.append("No compliance scan data available. Run a scan first.")
            
            lines.append("")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        else:
            return f"Unsupported format: {format_type}"
    
    def _save_compliance_results(self, results: Dict[str, List[PolicyViolation]]) -> None:
        """Save compliance results to file."""
        try:
            # Convert PolicyViolation objects to dictionaries for JSON serialization
            serializable_results = {}
            for project_path, violations in results.items():
                serializable_results[project_path] = [
                    {
                        "platform": v.platform,
                        "violation_type": v.violation_type.value,
                        "risk_level": v.risk_level.value,
                        "description": v.description,
                        "current_value": v.current_value,
                        "limit_value": v.limit_value,
                        "project_path": v.project_path,
                        "timestamp": v.timestamp,
                        "remediation_suggestion": v.remediation_suggestion,
                        "policy_reference": v.policy_reference
                    }
                    for v in violations
                ]
            
            with open(COMPLIANCE_RESULTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save compliance results: {e}")

def main():
    """Main entry point for the policy monitor."""
    parser = argparse.ArgumentParser(description="Professional Policy Monitoring System")
    parser.add_argument("--mode", choices=["monitor", "scan", "report", "update"], 
                       default="scan", help="Operation mode")
    parser.add_argument("--interval", type=int, default=3600,
                       help="Monitoring interval in seconds (for monitor mode)")
    parser.add_argument("--project", type=str, 
                       help="Specific project path to scan (for scan mode)")
    parser.add_argument("--format", choices=["text", "json"], 
                       default="text", help="Output format (for report mode)")
    parser.add_argument("--force-update", action="store_true",
                       help="Force policy update check (for update mode)")
    
    args = parser.parse_args()
    
    # Initialize the policy monitor
    monitor = PolicyMonitor()
    
    try:
        if args.mode == "monitor":
            logger.info("Starting policy monitoring mode")
            monitor.start_monitoring(args.interval)
            try:
                # Keep the main thread alive
                while monitor.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
            finally:
                monitor.stop_monitoring()
        
        elif args.mode == "scan":
            if args.project:
                # Scan specific project
                project_path = os.path.join(_KOK, args.project)
                if not os.path.isdir(project_path):
                    logger.error(f"Project not found: {args.project}")
                    sys.exit(1)
                
                violations = monitor.scan_project(project_path)
                print(f"Scan completed for {args.project}: {len(violations)} violations found")
                
                for violation in violations:
                    print(f"  [{violation.platform}] {violation.violation_type.value}: {violation.description}")
            else:
                # Scan all projects
                results = monitor.scan_all_content()
                total_violations = sum(len(v) for v in results.values())
                print(f"Full scan completed: {len(results)} projects with violations, {total_violations} total violations")
        
        elif args.mode == "report":
            report = monitor.generate_report(args.format)
            print(report)
        
        elif args.mode == "update":
            if args.force_update:
                logger.info("Forcing policy update check")
                updates = monitor.update_detector.detect_policy_updates()
                print(f"Policy update check completed: {len(updates)} updates detected")
                
                for update in updates:
                    print(f"  {update.platform}.{update.policy_area}: {update.old_value} → {update.new_value} ({update.change_type})")
            else:
                logger.info("Checking for policy updates")
                updates = monitor.update_detector.detect_policy_updates()
                print(f"Policy update check completed: {len(updates)} updates detected")
    
    except Exception as e:
        logger.error(f"Fatal error in policy monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()