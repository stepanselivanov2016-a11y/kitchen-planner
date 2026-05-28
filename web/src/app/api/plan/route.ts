import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${engineUrl}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();

      return NextResponse.json(
        {
          error: "Engine error",
          detail: text || `Engine returned HTTP ${res.status}`,
        },
        { status: 500 }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        error: "Engine unavailable",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
