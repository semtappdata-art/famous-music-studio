"""Onay sonucu veri yapısı — uyumluluk kapısı (uyumluluk.py) için."""

from dataclasses import dataclass, field
from typing import List, Tuple, Iterable


@dataclass(frozen=True)
class ApprovalResult:
    """
    Uyumluluk kontrolü sonucu.
    
    Tuple gibi davranır: `hatalar, uyarilar = result`
    Boolean olarak: `if result:` → hata varsa True (fail-closed)
    """
    hatalar: Tuple[str, ...] = field(default_factory=tuple)
    uyarilar: Tuple[str, ...] = field(default_factory=tuple)
    
    def __bool__(self) -> bool:
        """Fail-closed: hata varsa True (yani 'kapanır')."""
        return len(self.hatalar) > 0
    
    def __iter__(self):
        """Tuple unpacking: hatalar, uyarilar = result"""
        return iter((self.hatalar, self.uyarilar))
    
    def __len__(self) -> int:
        return len(self.hatalar) + len(self.uyarilar)
    
    @classmethod
    def from_lists(cls, hatalar: Iterable[str], uyarilar: Iterable[str]) -> "ApprovalResult":
        """Listelerden ApprovalResult oluştur."""
        return cls(
            hatalar=tuple(hatalar),
            uyarilar=tuple(uyarilar),
        )
    
    @classmethod
    def ok(cls, *uyarilar: str) -> "ApprovalResult":
        """Hatasız başarı sonucu."""
        return cls(hatalar=(), uyarilar=tuple(uyarilar))
    
    @classmethod
    def fail(cls, *hatalar: str) -> "ApprovalResult":
        """Hatalı sonuç."""
        return cls(hatalar=tuple(hatalar), uyarilar=())
    
    def merge(self, other: "ApprovalResult") -> "ApprovalResult":
        """İki sonucu birleştir (hatalar birikir)."""
        return ApprovalResult(
            hatalar=self.hatalar + other.hatalar,
            uyarilar=self.uyarilar + other.uyarilar,
        )
    
    def to_dict(self) -> dict:
        """Sözlüğe çevir (log/serialization için)."""
        return {
            "hatalar": list(self.hatalar),
            "uyarilar": list(self.uyarilar),
            "durum": "HATA" if self else "TAMAM",
        }