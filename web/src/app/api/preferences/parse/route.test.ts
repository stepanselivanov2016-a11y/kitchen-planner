import { afterEach, describe, expect, test, vi } from "vitest";

import { POST } from "./route";

describe("/api/preferences/parse route", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("proxies preference text to engine parser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            patch: { "room.upper_cabinet_opening": "lift" },
            locked: ["room.upper_cabinet_opening"],
            notes: [],
            source: "rules",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        )
      )
    );

    const response = await POST(
      new Request("http://localhost/api/preferences/parse", {
        method: "POST",
        body: JSON.stringify({ text: "верхние шкафы подъёмные" }),
      }) as never
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.patch["room.upper_cabinet_opening"]).toBe("lift");
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/preferences/parse",
      expect.objectContaining({ method: "POST" })
    );
  });
});
