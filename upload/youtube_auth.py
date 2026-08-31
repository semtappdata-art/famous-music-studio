"""YouTube Data API v3 OAuth2 kimlik doğrulama — bir kere tamamlanır, token.json'a kaydedilir.

Kullanım:
    python upload/youtube_auth.py

Önkoşul: Google Cloud Console'dan indirilen client_secrets.json bu klasörde
(upload/) bulunmalı. OAuth consent flow tarayıcıda açılır, kullanıcı Google
hesabıyla giriş yapar, token.json otomatik yazılır.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "token.json")


def get_authenticated_service():
    """Yetkilendirilmiş bir YouTube API client'ı döner. token.json varsa ve
    geçerliyse onu kullanır, süresi dolmuşsa yeniler, hiç yoksa tarayıcıda
    consent flow açar."""
    creds = None
    if os.path.isfile(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.isfile(CLIENT_SECRETS_PATH):
                raise FileNotFoundError(
                    f"client_secrets.json bulunamadı: {CLIENT_SECRETS_PATH}\n"
                    "Google Cloud Console > APIs & Services > Credentials > "
                    "OAuth 2.0 Client ID (Desktop app) indirip bu isimle buraya koy."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


if __name__ == "__main__":
    service = get_authenticated_service()
    print("Kimlik doğrulama başarılı, token.json yazıldı.")
