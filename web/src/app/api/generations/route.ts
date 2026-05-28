import { NextRequest, NextResponse } from "next/server";

function authHeaders(req: NextRequest): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  const authorization = req.headers.get("authorization");

  if (authorization) {
    headers.Authorization = authorization;
  }

  return headers;
}

export async function GET(req: NextRequest) {
  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  const res = await fetch(`${engineUrl}/generations`, {
    method: "GET",
    headers: authHeaders(req),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(req: NextRequest) {
  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  const res = await fetch(`${engineUrl}/generations`, {
    method: "POST",
    headers: authHeaders(req),
    body: await req.text(),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(req: NextRequest) {
  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  const res = await fetch(`${engineUrl}/generations`, {
    method: "DELETE",
    headers: authHeaders(req),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
