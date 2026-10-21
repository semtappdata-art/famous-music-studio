"""Analytics Automation — P2 #18

Haftalık KPI raporu + Telegram/e-posta bildirimi
- CTR, AVD, Abone artışı, Cross-promo trafiği
- En iyi/en kötü 3 video
- Kapak A/B test sonuçları
- Otomatik rapor: Telegram/e-posta
"""

import os
import json
import asyncio
import smtplib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

# Windows konsol kodlamasi (cp1254) emoji basamiyor — pipeline'daki
# "🚀 Haftalık..." print'i UnicodeEncodeError ile PATLATIYORDU.
# 2026-10-19: `gorev_sarmalayici` ile zamanlanmış koşuda bu, raporun
# tamamini kaybettirirdi. `dj_famous_process.py` ile ayni desen.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


@dataclass
class VideoMetrics:
    """Video metrikleri."""
    video_id: str
    title: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    avg_view_duration_pct: float = 0.0  # %
    avg_view_duration_sec: float = 0.0
    ctr: float = 0.0  # %
    impressions: int = 0
    subscribers_gained: int = 0
    published_at: str = ""
    playlist: str = ""
    is_short: bool = False
    is_dj_set: bool = False


@dataclass
class WeeklyKPI:
    """Haftalık KPI."""
    week_start: str
    week_end: str
    total_videos: int = 0
    total_views: int = 0
    total_watch_time_hours: float = 0.0
    avg_ctr: float = 0.0
    avg_avd: float = 0.0  # %
    total_subscribers_gained: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    new_subscribers_per_video: float = 0.0
    ctr_trend: str = "stable"  # up/down/stable
    avd_trend: str = "stable"
    
    # En iyi / en kötü
    top_3_videos: List[Dict] = field(default_factory=list)
    bottom_3_videos: List[Dict] = field(default_factory=list)
    
    # A/B test sonuçları
    ab_test_results: List[Dict] = field(default_factory=list)
    
    # Cross-promo
    cross_promo_clicks: int = 0
    cross_promo_conversions: int = 0
    
    # Shorts metrikleri
    shorts_views: int = 0
    shorts_avg_watch_time: float = 0.0
    shorts_swipe_away_rate: float = 0.0


class AnalyticsCollector:
    """YouTube Analytics verisi toplayıcı."""
    
    def __init__(self):
        self.data_dir = Path("analytics_data")
        self.data_dir.mkdir(exist_ok=True)
        self.weekly_file = Path("analytics_data") / f"weekly_{datetime.now().strftime('%Y_W%U')}.json"
    
    def collect_from_youtube_api(self, video_ids: List[str]) -> List[VideoMetrics]:
        """YouTube Analytics API'den veri çek (mock implementation)."""
        # Gerçek implementasyonda: YouTube Analytics API v2
        # Bu mock implementation
        metrics = []
        for vid in video_ids:
            # Mock data
            metrics.append(VideoMetrics(
                video_id=vid,
                title=f"Video {vid[:8]}",
                views=15000,
                likes=1200,
                comments=85,
                shares=120,
                avg_view_duration_pct=58.5,
                avg_view_duration_sec=180.5,
                ctr=6.2,
                impressions=25000,
                subscribers_gained=45,
                published_at=(datetime.now() - timedelta(days=7)).isoformat(),
                playlist="City Pulse Sessions",
                is_short=False,
                is_dj_set=True
            ))
        return metrics
    
    def collect_from_state_files(self) -> List[VideoMetrics]:
        """State dosyalarından video listesi al."""
        import glob
        import os
        
        metrics = []
        for state_file in glob.glob("projects/*/state.json") + glob.glob("dj_sets/*/state.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                # Meta.json'dan ek bilgi
                meta_path = os.path.join(os.path.dirname(state_file), "meta.json")
                meta = {}
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                
                video_id = state.get("youtube_video_id") or state.get("youtube_shorts_video_id")
                if not video_id:
                    continue
                
                # Mock analytics - gerçek implementasyonda API'den
                metrics.append(VideoMetrics(
                    video_id=state.get("youtube_video_id", ""),
                    title=meta.get("title", "Unknown"),
                    views=15000,  # Mock
                    likes=1200,
                    comments=85,
                    shares=120,
                    avg_view_duration_pct=58.5,
                    avg_view_duration_sec=180.5,
                    ctr=6.2,
                    impressions=25000,
                    subscribers_gained=45,
                    published_at=state.get("youtube_uploaded_at", ""),
                    playlist=meta.get("series", "Main"),
                    is_short=bool(state.get("youtube_shorts_video_id")),
                    is_dj_set=meta.get("theme") == "dj"
                ))
            except Exception as e:
                print(f"Error reading {state_file}: {e}")
        
        return metrics
    
    def calculate_weekly_kpi(self, metrics: List[VideoMetrics]) -> WeeklyKPI:
        """Haftalık KPI hesapla."""
        now = datetime.now()
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).replace(hour=0, minute=0, second=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Bu haftaki videolar
        this_week = [m for m in metrics if m.published_at and 
                     datetime.fromisoformat(m.published_at.replace('Z', '+00:00')).replace(tzinfo=None) >= week_start]
        
        if not this_week:
            return WeeklyKPI(
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat()
            )
        
        total_views = sum(m.views for m in this_week)
        total_watch_sec = sum(m.avg_view_duration_sec * m.views for m in this_week)
        total_watch_hours = total_watch_sec / 3600
        avg_ctr = sum(m.ctr for m in this_week) / len(this_week) if this_week else 0
        avg_avd = sum(m.avg_view_duration_pct for m in this_week) / len(this_week) if this_week else 0
        
        # En iyi / en kötü 3
        sorted_by_views = sorted(this_week, key=lambda x: x.views, reverse=True)
        top_3 = [{"video_id": m.video_id, "title": m.title, "views": m.views, "ctr": m.ctr, "avd": m.avg_view_duration_pct} for m in sorted_by_views[:3]]
        bottom_3 = [{"video_id": m.video_id, "title": m.title, "views": m.views, "ctr": m.ctr, "avd": m.avg_view_duration_pct} for m in sorted_by_views[-3:]]
        
        # Shorts metrikleri
        shorts = [m for m in this_week if m.is_short]
        shorts_views = sum(m.views for m in shorts)
        shorts_avd = sum(m.avg_view_duration_pct for m in shorts) / len(shorts) if shorts else 0
        
        return WeeklyKPI(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            total_videos=len(this_week),
            total_views=total_views,
            total_watch_time_hours=round(total_watch_hours, 1),
            avg_ctr=round(sum(m.ctr for m in this_week) / len(this_week), 2) if this_week else 0,
            avg_avd=round(sum(m.avg_view_duration_pct for m in this_week) / len(this_week), 2) if this_week else 0,
            total_subscribers_gained=sum(m.subscribers_gained for m in this_week),
            total_likes=sum(m.likes for m in this_week),
            total_comments=sum(m.comments for m in this_week),
            total_shares=sum(m.shares for m in this_week),
            new_subscribers_per_video=round(sum(m.subscribers_gained for m in this_week) / len(this_week), 1) if this_week else 0,
            top_3_videos=top_3,
            bottom_3_videos=bottom_3,
            shorts_views=shorts_views,
            shorts_avg_watch_time=round(shorts_avd, 1)
        )
    
    def detect_trends(self, current: WeeklyKPI, previous: WeeklyKPI) -> WeeklyKPI:
        """Trend tespiti."""
        if not previous:
            return current
        
        ctr_diff = current.avg_ctr - previous.avg_ctr
        avd_diff = current.avg_avd - previous.avg_avd
        
        if ctr_diff > 0.5:
            current.ctr_trend = "up"
        elif ctr_diff < -0.5:
            current.ctr_trend = "down"
        
        if avd_diff > 2:
            current.avd_trend = "up"
        elif avd_diff < -2:
            current.avd_trend = "down"
        
        return current
    
    def load_previous_week(self) -> Optional[WeeklyKPI]:
        """Önceki hafta KPI'sını yükle."""
        # Önceki hafta dosyasını bul
        prev_week = datetime.now() - timedelta(weeks=1)
        prev_file = Path("analytics_data") / f"weekly_{prev_week.strftime('%Y_W%U')}.json"
        # NEDEN prev_file: `prev_week` bir DATETIME'dir — `.exists()` ve
        # `open()` onun üzerinde çağrılınca AttributeError veriyordu
        # ("'datetime.datetime' object has no attribute 'exists'") ve haftalık
        # pipeline KPI hesabından SONRA ölüyordu. 2026-10-19.
        if prev_file.exists():
            with open(prev_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WeeklyKPI(**data)
        return None
    
    def save_weekly_kpi(self, kpi: WeeklyKPI):
        """Haftalık KPI'yi kaydet."""
        self.weekly_file.parent.mkdir(exist_ok=True)
        data = {
            "week_start": kpi.week_start,
            "week_end": kpi.week_end,
            "total_videos": kpi.total_videos,
            "total_views": kpi.total_views,
            "total_watch_time_hours": kpi.total_watch_time_hours,
            "avg_ctr": kpi.avg_ctr,
            "avg_avd": kpi.avg_avd,
            "total_subscribers_gained": kpi.total_subscribers_gained,
            "total_likes": kpi.total_likes,
            "total_comments": kpi.total_comments,
            "total_shares": kpi.total_shares,
            "new_subscribers_per_video": kpi.new_subscribers_per_video,
            "ctr_trend": kpi.ctr_trend,
            "avd_trend": kpi.avd_trend,
            "top_3_videos": kpi.top_3_videos,
            "bottom_3_videos": kpi.bottom_3_videos,
            "ab_test_results": kpi.ab_test_results,
            "cross_promo_clicks": kpi.cross_promo_clicks,
            "cross_promo_conversions": kpi.cross_promo_conversions,
            "shorts_views": kpi.shorts_views,
            "shorts_avg_watch_time": kpi.shorts_avg_watch_time,
            "shorts_swipe_away_rate": kpi.shorts_swipe_away_rate
        }
        self.weekly_file.parent.mkdir(exist_ok=True)
        with open(self.weekly_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class ReportGenerator:
    """Haftalık rapor üretici."""
    
    @staticmethod
    def generate_markdown_report(kpi: WeeklyKPI, previous: Optional[WeeklyKPI] = None) -> str:
        """Markdown formatında haftalık rapor."""
        lines = [
            f"# 📊 Haftalık Analitik Raporu",
            f"**Dönem:** {kpi.week_start[:10]} - {kpi.week_end[:10]}",
            f"**Oluşturulma:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📈 Özet KPI",
            f"| Metrik | Değer | Trendi |",
            f"|--------|-------|--------|",
            f"| Toplam Video | {kpi.total_videos} | — |",
            f"| Toplam Görüntüleme | {kpi.total_views:,} | — |",
            f"| Toplam İzlenme Süresi | {kpi.total_watch_time_hours:.1f} saat | — |",
            f"| Ort. CTR | %{kpi.avg_ctr:.2f} | {kpi.ctr_trend} |",
            f"| Ort. AVD | %{kpi.avg_avd:.1f} | {kpi.avd_trend} |",
            f"| Yeni Abone/Video | {kpi.new_subscribers_per_video:.1f} | — |",
            f"| Toplam Abone Artışı | +{kpi.total_subscribers_gained} | — |",
            "",
            "## 🏆 En İyi 3 Video",
        ]
        
        for i, v in enumerate(kpi.top_3_videos, 1):
            lines.append(f"{i}. **{v['title']}** — {v['views']:,} görüntüleme | CTR: %{v['ctr']:.2f} | AVD: %{v['avd']:.1f}")
        
        if not kpi.top_3_videos:
            lines.append("Veri yok")
        
        lines.extend([
            "",
            "## 📉 En Düşük 3 Video",
        ])
        
        for i, v in enumerate(kpi.bottom_3_videos, 1):
            lines.append(f"{i}. **{v['title']}** — {v['views']:,} görüntüleme | CTR: %{v['ctr']:.2f} | AVD: %{v['avd']:.1f}")
        
        if not kpi.bottom_3_videos:
            lines.append("Veri yok")
        
        # A/B Test sonuçları
        if kpi.ab_test_results:
            lines.extend([
                "",
                "## 🧪 A/B Test Sonuçları",
            ])
            for test in kpi.ab_test_results:
                lines.append(f"• **{test.get('video_title', 'Video')}**: {test.get('winner', 'A')} kazandı (izlenme süresi: {test.get('watch_time_diff', 'N/A')})")
        
        # Shorts metrikleri
        if kpi.shorts_views > 0:
            lines.extend([
                "",
                "## 📱 Shorts Metrikleri",
                f"| Metrik | Değer |",
                f"|--------|-------|",
                f"| Shorts Görüntüleme | {kpi.shorts_views:,} |",
                f"| Ort. İzlenme Süresi | %{kpi.shorts_avg_watch_time:.1f} |",
                f"| Swipe Away Rate | %{kpi.shorts_swipe_away_rate:.1f} |",
            ])
        
        # Cross-promo
        if kpi.cross_promo_clicks > 0:
            lines.extend([
                "",
                "## 🔗 Cross-Promo",
                f"| Tıklama | Dönüşüm | Oran |",
                f"|---------|---------|------|",
                f"| {kpi.cross_promo_clicks:,} | {kpi.cross_promo_conversions:,} | %{kpi.cross_promo_conversions/kpi.cross_promo_clicks*100:.1f}" if kpi.cross_promo_clicks > 0 else "| 0 | 0 | 0% |",
            ])
        
        # Karşılaştırma
        if previous:
            lines.extend([
                "",
                "## 📊 Hafta Karşılaştırması",
                f"| Metrik | Bu Hafta | Geçen Hafta | Değişim |",
                f"|--------|----------|-------------|---------|",
                f"| Görüntüleme | {kpi.total_views:,} | {previous.total_views:,} | {kpi.total_views - previous.total_views:+,} |",
                f"| CTR | %{kpi.avg_ctr:.2f} | %{previous.avg_ctr:.2f} | %{kpi.avg_ctr - previous.avg_ctr:+.2f} |",
                f"| AVD | %{kpi.avg_avd:.1f} | %{previous.avg_avd:.1f} | %{kpi.avg_avd - previous.avg_avd:+.1f} |",
                f"| Abone/Video | {kpi.new_subscribers_per_video:.1f} | {previous.new_subscribers_per_video:.1f} | {kpi.new_subscribers_per_video - previous.new_subscribers_per_video:+.1f} |",
            ])
        
        lines.extend([
            "",
            "---",
            f"*Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            f"*Kaynak: YouTube Analytics API + State dosyaları*"
        ])
        
        return "\n".join(lines)


class NotificationSender:
    """Bildirim gönderici (Telegram + Email)."""
    
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.email_to = os.getenv("EMAIL_TO", "")
    
    async def send_telegram(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Telegram mesajı gönder."""
        if not self.telegram_token or not self.telegram_chat_id:
            print("⚠️ Telegram credentials not configured")
            return False
        
        import aiohttp
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def send_email(self, subject: str, body: str, html: bool = True) -> bool:
        """E-posta gönder."""
        if not self.smtp_user or not self.smtp_pass or not self.email_to:
            print("⚠️ Email credentials not configured")
            return False
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.email_to
        
        if html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
    
    async def send_weekly_report(self, kpi: WeeklyKPI, previous: Optional[WeeklyKPI] = None):
        """Haftalık raporu Telegram ve Email ile gönder."""
        md_report = ReportGenerator.generate_markdown_report(kpi, None)  # previous optional
        
        # Telegram (uzun mesaj için parçalara böl)
        if self.telegram_token:
            # Telegram 4096 karakter limiti
            chunks = [md_report[i:i+4000] for i in range(0, len(md_report), 4000)]
            for chunk in chunks:
                await self.send_telegram(chunk)
                await asyncio.sleep(0.5)  # Rate limit
        
        # Email (HTML format)
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>📊 Haftalık Analitik Raporu</h2>
            <p><strong>Dönem:</strong> {kpi.week_start[:10]} - {kpi.week_end[:10]}</p>
            
            <table style="border-collapse: collapse; width: 100%;">
                <tr><th style="text-align:left;">Metrik</th><th>Değer</th><th>Trend</th></tr>
                <tr><td>Toplam Video</td><td>{kpi.total_videos}</td><td>—</td></tr>
                <tr><td>Toplam Görüntüleme</td><td>{kpi.total_views:,}</td><td>—</td></tr>
                <tr><td>İzlenme Süresi</td><td>{kpi.total_watch_time_hours:.1f} saat</td><td>—</td></tr>
                <tr><td>Ort. CTR</td><td>%{kpi.avg_ctr:.2f}</td><td>{kpi.ctr_trend}</td></tr>
                <tr><td>Ort. AVD</td><td>%{kpi.avg_avd:.1f}</td><td>{kpi.avd_trend}</td></tr>
                <tr><td>Yeni Abone/Video</td><td>{kpi.new_subscribers_per_video:.1f}</td><td>—</td></tr>
            </table>
            
            <h3>🏆 En İyi 3 Video</h3>
            <ol>
        """
        
        for v in kpi.top_3_videos:
            html_body += f"<li><strong>{v['title']}</strong> — {v['views']:,} görüntüleme | CTR: %{v['ctr']:.2f} | AVD: %{v['avd']:.1f}</li>"
        
        html_body += """
            </ol>
            <hr>
            <p><small>Oluşturulma: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</small></p>
        </body></html>
        """
        
        # Telegram gönder
        await self.send_telegram(md_report[:4000])
        
        # Email gönder
        if self.email_to:
            self.send_email(
                subject=f"📊 Haftalık Analitik Raporu - {datetime.now().strftime('%Y-W%U')}",
                body=html_body,
                html=True
            )


class WeeklyReportPipeline:
    """Haftalık rapor pipeline'ı."""
    
    def __init__(self):
        self.collector = AnalyticsCollector()
        self.generator = ReportGenerator()
        self.notifier = NotificationSender()
    
    async def run_weekly_pipeline(self) -> bool:
        """Haftalık pipeline'ı çalıştır."""
        print("🚀 Haftalık analitik pipeline başlıyor...")
        
        # 1. Veri topla
        print("📥 Veri toplanıyor...")
        metrics = self.collector.collect_from_state_files()
        print(f"  {len(metrics)} video bulundu")
        
        # 2. KPI hesapla
        print("📊 KPI hesaplanıyor...")
        kpi = self.collector.calculate_weekly_kpi(metrics)
        
        # Önceki hafta ile karşılaştır
        prev = self.collector.load_previous_week()
        kpi = self.collector.detect_trends(kpi, prev)
        
        # Kaydet
        self.collector.save_weekly_kpi(kpi)
        
        # 3. Rapor üret
        print("📝 Rapor üretiliyor...")
        markdown_report = ReportGenerator.generate_markdown_report(kpi, None)
        
        # 4. Bildirim gönder
        print("📤 Bildirimler gönderiliyor...")
        notifier = NotificationSender()
        await notifier.send_weekly_report(kpi, None)
        
        print("✅ Haftalık pipeline tamamlandı!")
        return True
    
    def run_manual(self):
        """Manuel çalıştırma (cron için)."""
        asyncio.run(self.run_weekly_pipeline())


# CLI
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analytics Automation Pipeline")
    parser.add_argument("--run", action="store_true", help="Pipeline'ı çalıştır")
    parser.add_argument("--test-notification", action="store_true", help="Test bildirimi gönder")
    args = parser.parse_args()
    
    pipeline = WeeklyReportPipeline()
    
    if args.run:
        await pipeline.run_weekly_pipeline()
    elif args.test_notification:
        # Test bildirimi
        notifier = NotificationSender()
        test_kpi = WeeklyKPI(
            week_start=(datetime.now() - timedelta(days=7)).isoformat(),
            week_end=datetime.now().isoformat(),
            total_videos=8,
            total_views=125000,
            total_watch_time_hours=1250.5,
            avg_ctr=5.8,
            avg_avd=52.3,
            total_subscribers_gained=420,
            total_likes=8500,
            total_comments=450,
            total_shares=1200,
            new_subscribers_per_video=52.5,
            ctr_trend="up",
            avd_trend="stable",
            top_3_videos=[
                {"title": "City Pulse Ep04 Berlin", "views": 25000, "ctr": 6.5, "avd": 58.2},
                {"title": "Night Drive Ep02 LA", "views": 18000, "ctr": 5.2, "avd": 55.1},
                {"title": "Deep Focus Ep01 Bali", "views": 15000, "ctr": 4.8, "avd": 62.3}
            ],
            bottom_3_videos=[
                {"title": "TR05 Collab", "views": 3200, "ctr": 3.1, "avd": 42.1},
                {"title": "TR04 Organic House", "views": 4100, "ctr": 3.8, "avd": 45.3},
                {"title": "TR03 Melodic Bridge", "views": 4500, "ctr": 4.2, "avd": 48.7}
            ],
            shorts_views=45000,
            shorts_avg_watch_time=68.5,
            shorts_swipe_away_rate=12.3
        )
        
        notifier = NotificationSender()
        await notifier.send_weekly_report(test_kpi, None)
        print("Test notification sent")
    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())