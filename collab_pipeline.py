"""Collab Pipeline — P2 #15

Stem paylaşımı + onay takibi + solo fallback
"""

import os
import json
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import config


class CollabStatus(Enum):
    PENDING = "pending"          # İstek gönderildi
    STEMS_SHARED = "stems_shared"  # Stemler paylaşıldı
    IN_PROGRESS = "in_progress"    # Ortak çalışma devam ediyor
    REVIEW = "review"              # İnceleme bekliyor
    APPROVED = "approved"          # Onaylandı
    REJECTED = "rejected"          # Reddedildi
    FALLBACK_SOLO = "fallback_solo" # Solo versiyon üretildi
    COMPLETED = "completed"        # Tamamlandı, upload hazır


@dataclass
class CollabPartner:
    """İşbirliği ortağı."""
    name: str
    handle: str  # @handle veya email
    platform: str  # "soundcloud", "email", "drive", "dropbox"
    contact: str   # URL veya email
    role: str      # "producer", "vocalist", "instrumentalist", "mixer"
    stem_access: str  # "drive_folder", "soundcloud_private", "email_attachment"
    notes: str = ""


@dataclass
class CollabProject:
    """İşbirliği projesi."""
    id: str
    title: str
    project_dir: str
    owner: str  # "DJ Famous"
    partner: CollabPartner
    status: CollabStatus = CollabStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Stem dosyaları
    stems: Dict[str, str] = field(default_factory=dict)  # {"drums": "path", "bass": "path"}
    
    # İşbirliği metadata
    stem_shared_at: Optional[str] = None
    review_requested_at: Optional[str] = None
    approved_at: Optional[str] = None
    fallback_triggered_at: Optional[str] = None
    
    # Sonuç
    final_audio_id: Optional[str] = None  # Suno audio_id
    solo_version: bool = False
    fallback_reason: str = ""
    
    # Onay takibi
    approval_token: str = ""  # Güvenli onay linki için token
    approval_expires: str = ""  # ISO timestamp
    
    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "project_dir": self.project_dir,
            "owner": self.owner,
            "partner": {
                "name": self.partner.name,
                "handle": self.partner.handle,
                "platform": self.partner.platform,
                "contact": self.partner.contact,
                "role": self.partner.role,
                "stem_access": self.partner.stem_access,
                "notes": self.partner.notes
            },
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stems": self.stems,
            "stem_shared_at": self.stem_shared_at,
            "review_requested_at": self.review_requested_at,
            "approved_at": self.approved_at,
            "fallback_triggered_at": self.fallback_triggered_at,
            "final_audio_id": self.final_audio_id,
            "solo_version": self.solo_version,
            "fallback_reason": self.fallback_reason,
            "approval_token": self.approval_token,
            "approval_expires": self.approval_expires
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CollabProject":
        partner = CollabPartner(**data["partner"])
        obj = cls(
            id=data["id"],
            title=data["title"],
            project_dir=data["project_dir"],
            owner=data["owner"],
            partner=partner,
            status=CollabStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            stems=data.get("stems", {}),
            stem_shared_at=data.get("stem_shared_at"),
            review_requested_at=data.get("review_requested_at"),
            approved_at=data.get("approved_at"),
            fallback_triggered_at=data.get("fallback_triggered_at"),
            final_audio_id=data.get("final_audio_id"),
            solo_version=data.get("solo_version", False),
            fallback_reason=data.get("fallback_reason", ""),
            approval_token=data.get("approval_token", ""),
            approval_expires=data.get("approval_expires", "")
        )
        return obj


class CollabManager:
    """İşbirliği yöneticisi."""
    
    def __init__(self, base_dir: str = "collabs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.index_file = self.base_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        self.index_file.parent.mkdir(exist_ok=True)
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {"projects": {}}
    
    def _save_index(self):
        self.index_file.parent.mkdir(exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def create_project(self, 
                       title: str,
                       partner: CollabPartner,
                       owner: str = "DJ Famous") -> CollabProject:
        """Yeni işbirliği projesi oluştur."""
        import uuid
        project_id = f"collab_{uuid.uuid4().hex[:8]}"
        
        project = CollabProject(
            id=project_id,
            title=title,
            project_dir=str(Path("collabs") / f"collab_{uuid.uuid4().hex[:8]}"),
            owner="DJ Famous",
            partner=partner
        )
        
        # Proje dizini oluştur
        project_path = Path(project.project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        
        # State kaydet
        self._save_project(project)
        self.index["projects"][project.id] = {
            "title": project.title,
            "partner": partner.name,
            "status": project.status.value,
            "created_at": project.created_at,
            "dir": project.project_dir
        }
        self._save_index()
        
        return project
    
    def _project_path(self, project_id: str) -> Path:
        return self.base_dir / project_id
    
    def _save_project(self, project: CollabProject):
        project_dir = self._project_path(project.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        state_file = project_dir / "state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_project(self, project_id: str) -> Optional[CollabProject]:
        project_dir = self._project_path(project_id)
        state_file = project_dir / "state.json"
        if not state_file.exists():
            return None
        with open(state_file, "r", encoding="utf-8") as f:
            return CollabProject.from_dict(json.load(f))
    
    def share_stems(self, project_id: str, stem_paths: Dict[str, str]) -> bool:
        """Stem dosyalarını paylaş (Google Drive, SoundCloud private, vs.)."""
        project = self.load_project(project_id)
        if not project:
            return False
        
        project.stems = stem_paths
        project.stem_shared_at = datetime.now().isoformat()
        project.status = CollabStatus.STEMS_SHARED
        project.update_timestamp()
        self._save_project(project)
        return True
    
    def request_review(self, project_id: str, approval_expires_hours: int = 168) -> str:
        """İnceleme isteği gönder (onay token'ı üret)."""
        import secrets
        project = self.load_project(project_id)
        if not project:
            return ""
        
        import secrets
        project.approval_token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=168)  # 1 hafta
        project.approval_expires = (datetime.now() + timedelta(hours=approval_expires_hours)).isoformat()
        project.review_requested_at = datetime.now().isoformat()
        project.status = CollabStatus.REVIEW
        project.update_timestamp()
        self._save_project(project)
        
        # Onay linki üret (gerçek implementasyonda web endpoint'e yönlendirir)
        approval_link = f"https://approve.collab/{project.id}?token={project.approval_token}"
        return approval_link
    
    def approve(self, project_id: str, token: str) -> bool:
        """Onayla."""
        project = self.load_project(project_id)
        if not project or project.approval_token != token:
            return False
        
        if datetime.fromisoformat(project.approval_expires) < datetime.now():
            return False  # Süresi doldu
        
        project.approved_at = datetime.now().isoformat()
        project.status = CollabStatus.APPROVED
        project.update_timestamp()
        self._save_project(project)
        return True
    
    def reject(self, project_id: str, reason: str = "") -> bool:
        """Reddet."""
        project = self.load_project(project_id)
        if not project:
            return False
        
        project.status = CollabStatus.REJECTED
        project.fallback_reason = reason or "Partner rejected"
        project.update_timestamp()
        self._save_index()
        return True
    
    def trigger_fallback(self, project_id: str, reason: str = "Collab approval timeout") -> bool:
        """Fallback: solo versiyon üret."""
        project = self.load_project(project_id)
        if not project:
            return False
        
        project.fallback_triggered_at = datetime.now().isoformat()
        project.fallback_reason = reason
        project.status = CollabStatus.FALLBACK_SOLO
        project.solo_version = True
        project.update_timestamp()
        self._save_index()
        return True
    
    def complete(self, project_id: str, final_audio_id: str) -> bool:
        """Tamamla."""
        project = self.load_project(project_id)
        if not project:
            return False
        
        project.final_audio_id = final_audio_id
        project.status = CollabStatus.COMPLETED
        project.update_timestamp()
        self._save_index()
        return True
    
    def check_fallback_timeouts(self) -> List[str]:
        """Süresi dolan collab'ler için fallback tetikle."""
        triggered = []
        for project_id, info in self.index["projects"].items():
            project = self.load_project(project_id)
            if not project:
                continue
            
            if project.status == CollabStatus.REVIEW:
                if project.approval_expires and datetime.fromisoformat(project.approval_expires) < datetime.now():
                    self.trigger_fallback(project.id, "Approval timeout")
                    triggered.append(project_id)
            elif project.status == CollabStatus.STEMS_SHARED:
                # Stem paylaşıldı ama 2 hafta geçtiyse
                if project.stem_shared_at:
                    shared = datetime.fromisoformat(project.stem_shared_at)
                    if (datetime.now() - shared).days > 14:
                        self.trigger_fallback(project.id, "No review after 2 weeks")
                        triggered.append(project_id)
        return triggered
    
    def get_pending_reviews(self) -> List[CollabProject]:
        """Bekleyen incelemeleri getir."""
        pending = []
        for project_id in self.index["projects"]:
            project = self.load_project(project_id)
            if project and project.status in [CollabStatus.REVIEW, CollabStatus.STEMS_SHARED]:
                pending.append(project)
        return pending


# CLI
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Collab Pipeline Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    # Create
    create_parser = subparsers.add_parser("create", help="Yeni collab projesi")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--partner-name", required=True)
    create_parser.add_argument("--partner-handle", required=True)
    create_parser.add_argument("--partner-platform", default="soundcloud")
    create_parser.add_argument("--partner-contact", required=True)
    create_parser.add_argument("--partner-role", default="producer")
    create_parser.add_argument("--partner-stem-access", default="drive_folder")
    create_parser.add_argument("--partner-notes", default="")
    
    # List
    list_parser = subparsers.add_parser("list", help="Projeleri listele")
    
    # Share stems
    share_parser = subparsers.add_parser("share-stems", help="Stem paylaş")
    share_parser.add_argument("--project-id", required=True)
    share_parser.add_argument("--stems", required=True, help="JSON: {'drums': 'path', 'bass': 'path'}")
    
    # Request review
    review_parser = subparsers.add_parser("request-review", help="İnceleme iste")
    review_parser.add_argument("--project-id", required=True)
    
    # Approve
    approve_parser = subparsers.add_parser("approve", help="Onayla")
    approve_parser.add_argument("--project-id", required=True)
    approve_parser.add_argument("--token", required=True)
    
    # Fallback
    fallback_parser = subparsers.add_parser("fallback", help="Fallback tetikle")
    fallback_parser.add_argument("--project-id", required=True)
    fallback_parser.add_argument("--reason", default="Timeout")
    
    # Check timeouts
    timeout_parser = subparsers.add_parser("check-timeouts", help="Süresi dolanları kontrol et")
    
    args = parser.parse_args()
    
    manager = CollabManager()
    
    if args.command == "create":
        partner = CollabPartner(
            name=args.partner_name,
            handle=args.partner_handle,
            platform=args.partner_platform,
            contact=args.partner_contact,
            role=args.partner_role,
            stem_access=args.partner_stem_access,
            notes=args.partner_notes
        )
        project = manager.create_project(args.title, partner)
        print(f"Created: {project.id} - {project.title}")
    
    elif args.command == "list":
        for pid, info in manager.index["projects"].items():
            status = "✅" if info["status"] == "completed" else "⏳"
            print(f"{status} {pid}: {info['title']} ({info['partner']}) - {info['status']}")
    
    elif args.command == "share-stems":
        stems = json.loads(args.stems)
        if manager.share_stems(args.project_id, stems):
            print("Stems shared")
        else:
            print("Failed")
    
    elif args.command == "request-review":
        link = manager.request_review(args.project_id)
        print(f"Review link: {link}")
    
    elif args.command == "approve":
        if manager.approve(args.project_id, args.token):
            print("Approved")
        else:
            print("Failed")
    
    elif args.command == "fallback":
        if manager.trigger_fallback(args.project_id, args.reason):
            print("Fallback triggered")
        else:
            print("Failed")
    
    elif args.command == "check-timeouts":
        triggered = manager.check_fallback_timeouts()
        print(f"Triggered fallbacks: {triggered}")


if __name__ == "__main__":
    main()