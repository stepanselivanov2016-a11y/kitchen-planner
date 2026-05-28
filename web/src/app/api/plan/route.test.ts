import { afterEach, describe, expect, test, vi } from "vitest";

import { POST } from "./route";

function jsonRequest(payload: unknown) {
  return new Request("http://localhost/api/plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

describe("/api/plan route", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("returns generated layout from engine", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ front_view_svg: "<svg />" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    const response = await POST(jsonRequest({ prompt: "Кухня 3000 мм" }) as never);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.front_view_svg).toBe("<svg />");
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/generate",
      expect.objectContaining({ method: "POST" })
    );
  });

  test("wraps non-ok engine response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("boom", { status: 500 }))
    );

    const response = await POST(jsonRequest({ prompt: "bad" }) as never);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe("Engine error");
    expect(data.detail).toBe("boom");
  });
});
