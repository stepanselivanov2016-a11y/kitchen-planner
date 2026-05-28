import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const engineUrl =
    process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${engineUrl}/preferences/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await req.text(),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Не удалось подключиться к модулю распознавания.",
      },
      { status: 500 }
    );
  }
}
