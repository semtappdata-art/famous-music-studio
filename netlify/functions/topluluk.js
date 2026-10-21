/**
 * Famous Music Studio — topluluk abonelik fonksiyonu (Netlify Functions, JS).
 *
 * NEDEN JS (2026-10-21): Netlify Lambda'da Python desteklenmiyor.
 * Python surumu yerelde calisir: site/api/topluluk.py
 *
 * DEPOLAMA: Netlify Blobs v1.6.1 (bkz. analytics.js).
 *
 * PII: sadece e-posta adresi (topluluk listesi icin gerekli).
 * Ziyaret analitiginden AYRI tutulur.
 * Cift kayit engellenir.
 */
import { Blobs } from "@netlify/blobs";

const ABONE_STORE = "topluluk-aboneler";
const LOG_STORE = "topluluk-bildirimler";
// ntfy: Discord bu agdan erisilemez, Telegram icin gercek token gerekli.
// ntfy token gerektirmez, telefona anlik push gonderir.
const NTFY_TOPIC = process.env.NTFY_TOPIC || "fms-t38y77gjd6r7a7h649mb16w2";
const NTFY_SERVER = process.env.NTFY_SERVER || "https://ntfy.sh";
const ALLOWED_ORIGINS = new Set([
  "https://famousmusicstudio.com",
  "https://www.famousmusicstudio.com",
  "https://famous-music-studio.netlify.app",
  "https://semtappdata-art.github.io",
]);
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

function storeOlustur(context) {
  const token = process.env.NETLIFY_BLOBS_TOKEN;
  const siteID = process.env.NETLIFY_SITE_ID;
  if (context && context.blobs && context.blobs.token) {
    return new Blobs({
      authentication: { contextURL: context.blobs.url, token: context.blobs.token },
      siteID: siteID || (context && context.blobs.siteID),
    });
  }
  if (token) {
    return new Blobs({ authentication: { token }, siteID });
  }
  return null;
}

async function ntfyGonder(baslik, mesaj, link) {
  if (!NTFY_TOPIC) return false;
  try {
    const govde = mesaj + (link ? "\n\n" + link : "");
    // HTTP header'lar latin-1'dir; Turkce karakter/em-dash header'da PATLAR.
    const temizBaslik = String(baslik)
      .replace(/—/g, "-")
      .replace(/–/g, "-")
      .replace(/[^\x20-\x7E]/g, "")
      .slice(0, 200);
    const r = await fetch(NTFY_SERVER + "/" + encodeURIComponent(NTFY_TOPIC), {
      method: "POST",
      headers: {
        "Title": temizBaslik || "Famous Music Studio",
        "Content-Type": "text/plain; charset=utf-8",
        "Priority": "default",
        "Tags": "music,headphones",
      },
      body: govde,
    });
    return r.ok;
  } catch (e) {
    return false;
  }
}

export default async (req, context) => {
  const origin = req.headers.get("origin") || "";
  const corsOrigin = ALLOWED_ORIGINS.has(origin) ? origin : "*";
  const headers = {
    "Access-Control-Allow-Origin": corsOrigin,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "600",
  };

  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });

  const store = storeOlustur(context);
  if (!store) {
    return new Response(JSON.stringify({ hata: "depolama yapilandirilmamis" }), {
      status: 503, headers: { ...headers, "Content-Type": "application/json" },
    });
  }

  // GET — ozet
  if (req.method === "GET") {
    const liste = (await store.get("abone", { type: "json" })) || [];
    return new Response(
      JSON.stringify({
        toplam: liste.length,
        onayli: liste.filter((a) => a.onay).length,
      }),
      { status: 200, headers: { ...headers, "Content-Type": "application/json" } }
    );
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ hata: "sadece POST" }), {
      status: 405, headers: { ...headers, "Content-Type": "application/json" },
    });
  }

  try {
    const ham = await req.text();
    let body = {};
    try { body = ham ? JSON.parse(ham) : {}; } catch { body = {}; }
    if (!body || typeof body !== "object") body = {};

    const email = String(body.email || "").trim().toLowerCase();
    if (!EMAIL_RE.test(email) || email.length > 254) {
      return new Response(JSON.stringify({ hata: "gecersiz e-posta" }), {
        status: 400, headers: { ...headers, "Content-Type": "application/json" },
      });
    }

    const liste = (await store.get("abone", { type: "json" })) || [];
    if (liste.some((a) => a.email === email)) {
      return new Response(null, { status: 204, headers });
    }

    liste.push({
      email,
      kaynak: String(body.kaynak || "site").slice(0, 40),
      zaman: new Date().toISOString(),
      onay: false,
    });
    await store.set("abone", JSON.stringify(liste), { type: "json" });

    // ntfy anlik bildirimi (telefona push)
    await ntfyGonder(
      String(body.baslik || "Yeni Video"),
      String(body.mesaj || "Famous Music Studio'da yeni bir sey var."),
      String(body.link || "")
    );

    // Bildirim logu
    const logStore = storeOlustur(context);
    const loglar = (await logStore.get("log", { type: "json" })) || [];
    loglar.push({
      zaman: new Date().toISOString(),
      baslik: String(body.baslik || "Yeni içerik").slice(0, 120),
      mesaj: String(body.mesaj || "").slice(0, 2000),
      link: String(body.link || "").slice(0, 300),
      alici_sayisi: liste.length,
    });
    await logStore.set("log", JSON.stringify(loglar), { type: "json" });

    return new Response(null, { status: 204, headers });
  } catch (e) {
    return new Response(JSON.stringify({ hata: String(e).slice(0, 160) }), {
      status: 400, headers: { ...headers, "Content-Type": "application/json" },
    });
  }
};
