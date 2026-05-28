import { NextRequest, NextResponse } from "next/server";

function authHeaders(req: NextRequest): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  const authorization = req.headers.get("authorization");

  if (authorization) {
    headers.Authorization = authorization;
  }

  return headers;
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  const res = await fetch(`${engineUrl}/generations/${id}`, {
    method: "DELETE",
    headers: authHeaders(req),
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
