import { NextResponse } from "next/server";

const headers = { "Cache-Control": "no-store" };
const fail = (error: string, status: number) => NextResponse.json({ error }, { status, headers });

export async function POST(req: Request) {
  const authorization = req.headers.get("authorization");
  if (!authorization || !/^Bearer \S+$/.test(authorization)) return fail("CLINIC_LOGIN_REQUIRED", 401);
  let body;
  try { body = await req.json(); } catch { return fail("INVALID_REQUEST", 400); }
  if (!body || typeof body !== "object" || Array.isArray(body) ||
      Object.keys(body).sort().join(",") !== "access_token,password" ||
      typeof body.password !== "string" || !body.password || body.password.length > 1024 ||
      typeof body.access_token !== "string" || !body.access_token || body.access_token.length > 4096) {
    return fail("INVALID_REQUEST", 400);
  }
  const configured = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!configured) return fail("LINK_SERVICE_UNAVAILABLE", 503);
  try {
    const base = new URL(configured);
    if (base.username || base.password || base.search || base.hash ||
        (base.protocol !== "https:" && !(base.protocol === "http:" && ["localhost", "127.0.0.1"].includes(base.hostname)))) {
      return fail("LINK_SERVICE_UNAVAILABLE", 503);
    }
    base.pathname = base.pathname.replace(/\/$/, "").replace(/\/api$/, "") + "/api/line/verified-link/";
    const res = await fetch(base, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: authorization },
      body: JSON.stringify({ password: body.password, access_token: body.access_token }),
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(20000),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const known = new Set(["LINE_LINK_CONFLICT", "LINE_TOKEN_INVALID", "LINE_PROFILE_INVALID",
        "CLINIC_PATIENT_IDENTITY_AMBIGUOUS", "LINE_VERIFICATION_UNAVAILABLE"]);
      const code = known.has(data?.error) ? data.error :
        res.status === 401 ? "CLINIC_LOGIN_REQUIRED" : res.status === 403 ? "PASSWORD_CONFIRMATION_FAILED" : "LINK_SERVICE_UNAVAILABLE";
      return fail(code, [400, 401, 403, 409, 429, 503].includes(res.status) ? res.status : 502);
    }
    if (data?.success !== true || !["LINKED", "ALREADY_LINKED"].includes(data.status)) {
      return fail("INVALID_LINK_RESPONSE", 502);
    }
    return NextResponse.json({ success: true, status: data.status }, { headers });
  } catch {
    return fail("LINK_SERVICE_UNAVAILABLE", 503);
  }
}
