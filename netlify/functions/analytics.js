/**
 * Famous Music Studio — analitik fonksiyonu (Netlify Functions, JS).
 *
 * NEDEN JS (2026-10-21): Netlify Lambda fonksiyonlarinda Python DESTEKLENMIYOR
 * ("you can deploy functions built with TypeScript, JavaScript, and Go").
 * Python surumu yerelde calisir: site/api/analytics.py
 *
 * DEPOLAMA: Netlify Blobs v1.6.1. Blobs, Netlify Functions icinde
 * `context.blobs` ile gelen kimlik bilgisiyle calisir; token gerekiyorsa
 * NETLIFY_BLOBS_TOKEN + NETLIFY_SITE_ID environment variable'larindan okunur.
 *
 * PII YOK, cookie YOK, fingerprint YOK. Toplanan: zaman, sayfa yolu,
 * referrer host, cihaz tipi, dil, saat dilimi, viewport.
 */
import { Blobs } from "@netlify/blobs";

const LOG_STORE = "site-visits";
const MAX_ENTRIES = 20000;
const ALLOWED_ORIGINS = new Set([
  "https://famousmusicstudio.com",
  "https://www.famousmusicstudio.com",
  "https://famous-music-studio.netlify.app",
  "https://semtappdata-art.github.io",
]);

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

function guvenliYol(yol) {
  if (!yol) return "/";
  const t = String(yol).split("?")[0].split("#")[0];
  return /^\/[A-Za-z0-9/_.\-]{0,180}$/.test(t) ? t.slice(0, 180) : "/";
}

function cihazTipi(userAgent, genislik) {
  const ua = userAgent || "";
  if (/iPad|Tablet/i.test(ua) || (genislik > 640 && /Android/i.test(ua) && !/Mobile/i.test(ua))) return "tablet";
  if (genislik <= 640 || /Mobile|Android|iPhone/i.test(ua)) return "mobil";
  return "masaustu";
}

function referrerHost(ref, origin) {
  if (!ref) return "-";
  try {
    if (ref.indexOf(origin) === 0) return "(site)";
    return new URL(ref).host;
  } catch {
    return "-";
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
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ hata: "sadece POST" }), {
      status: 405, headers: { ...headers, "Content-Type": "application/json" },
    });
  }

  const store = storeOlustur(context);
  if (!store) {
    return new Response(JSON.stringify({ hata: "depolama yapilandirilmamis" }), {
      status: 503, headers: { ...headers, "Content-Type": "application/json" },
    });
  }

  try {
    // Content-Type text/plain oldugu icin govdeyi metin olarak al
    const ham = await req.text();
    let body = {};
    try { body = ham ? JSON.parse(ham) : {}; } catch { body = {}; }
    if (!body || typeof body !== "object") body = {};

    const kayit = {
      ts: new Date().toISOString(),
      path: guvenliYol(body.path),
      ref: referrerHost(body.ref, origin),
      device: cihazTipi(body.ua, Number(body.vw) || 0),
      lang: String(body.lang || "tr").slice(0, 5),
      tz: String(body.tz || "bilinmiyor").slice(0, 60),
      vp: String(body.vp || "").slice(0, 16),
      app: "famous-music-studio",
    };

    const kayitlar = (await store.get("visits", { type: "json" })) || [];

    // Cift yazma korumasi: ayni path, son 5 dakika
    const yeni = Date.now();
    const son5dk = kayitlar.filter(
      (k) => k.path === kayit.path && yeni - Date.parse(k.ts) < 300000
    );
    if (son5dk.length === 0) {
      kayitlar.push(kayit);
      if (kayitlar.length > MAX_ENTRIES) {
        kayitlar.splice(0, kayitlar.length - MAX_ENTRIES);
      }
      await store.set("visits", JSON.stringify(kayitlar), { type: "json" });
    }

    return new Response(null, { status: 204, headers });
  } catch (e) {
    return new Response(JSON.stringify({ hata: String(e).slice(0, 160) }), {
      status: 400, headers: { ...headers, "Content-Type": "application/json" },
    });
  }
};
