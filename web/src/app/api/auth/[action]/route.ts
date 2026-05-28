import { NextRequest, NextResponse } from "next/server";

const allowedActions = new Set(["register", "login", "me", "change-password"]);

async function proxyAuthRequest(
  req: NextRequest,
  action: string,
  method: "GET" | "POST"
) {
  if (!allowedActions.has(action)) {
    return NextResponse.json({ error: "Unknown auth action" }, { status: 404 });
  }

  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";
  const headers: HeadersInit = { "Content-Type": "application/json" };
  const authorization = req.headers.get("authorization");

  if (authorization) {
    headers.Authorization = authorization;
  }

  const res = await fetch(`${engineUrl}/auth/${action}`, {
    method,
    headers,
    body: method === "POST" ? await req.text() : undefined,
  });

  const text = await res.text();
  const payload = text ? JSON.parse(text) : {};

  return NextResponse.json(payload, { status: res.status });
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ action: string }> }
) {
  const { action } = await context.params;
  return proxyAuthRequest(req, action, "GET");
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ action: string }> }
) {
  const { action } = await context.params;
  return proxyAuthRequest(req, action, "POST");
}
