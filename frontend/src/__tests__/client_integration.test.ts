import { describe, it, expect, beforeAll, afterAll } from "vitest";
import http from "node:http";
import { api, setCsrfToken, setBaseUrl } from "../api/client";

describe("Typed Frontend Client - Real HTTP Boundary Integration", () => {
  let server: http.Server;
  let serverUrl: string;

  beforeAll(async () => {
    server = http.createServer((req, res) => {
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Access-Control-Allow-Headers", "*");
      res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");

      if (req.method === "OPTIONS") {
        res.writeHead(204);
        res.end();
        return;
      }

      if (req.url === "/api/v1/auth/csrf-token" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ csrf_token: "socket-csrf-tok-999" }));
        return;
      }

      if (req.url === "/api/v1/experiments" && req.method === "POST") {
        let body = "";
        req.on("data", chunk => { body += chunk; });
        req.on("end", () => {
          const payload = JSON.parse(body);
          const csrf = req.headers["x-csrf-token"];
          if (!csrf) {
            res.writeHead(403, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ detail: "Missing CSRF token" }));
            return;
          }
          res.writeHead(201, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            id: "exp_http_777",
            name: payload.name,
            description: payload.description || null,
            domain: payload.domain || "ai-ml",
            baseline_variant: payload.baseline_variant || null,
            created_by: "ryandtvo@gmail.com",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            run_count: 0,
          }));
        });
        return;
      }

      if (req.url?.startsWith("/api/v1/experiments?") && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          items: [
            {
              id: "exp_http_777",
              name: "Socket Bound Transformer",
              domain: "ai-ml",
              created_by: "ryandtvo@gmail.com",
              run_count: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          pages: 1,
        }));
        return;
      }

      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "Not found" }));
    });

    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address() as { port: number };
        serverUrl = `http://127.0.0.1:${addr.port}`;
        setBaseUrl(serverUrl);
        resolve();
      });
    });
  });

  afterAll(async () => {
    setBaseUrl("");
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("crosses real HTTP boundary to fetch CSRF token and create experiment", async () => {
    setCsrfToken(null);
    const created = await api.experiments.create({
      name: "Socket Bound Transformer",
      domain: "ai-ml",
      baseline_variant: "base",
    });

    expect(created).toBeDefined();
    expect(created.id).toBe("exp_http_777");
    expect(created.name).toBe("Socket Bound Transformer");
    expect(created.created_by).toBe("ryandtvo@gmail.com");
  });

  it("crosses real HTTP boundary to list experiments with envelope decoding", async () => {
    const list = await api.experiments.list(1, 50);

    expect(list.total).toBe(1);
    expect(list.items).toHaveLength(1);
    expect(list.items[0].id).toBe("exp_http_777");
    expect(list.items[0].domain).toBe("ai-ml");
  });
});
