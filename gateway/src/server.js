import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";

import { config } from "./config.js";

const app = express();

app.use(helmet());
app.use(cors({
  origin(origin, callback) {
    if (!origin || config.corsOrigins.includes(origin)) {
      callback(null, true);
      return;
    }
    callback(new Error("CORS origin is not allowed"));
  },
  credentials: true,
}));
app.use(express.json({ limit: "2mb" }));
app.use(morgan("combined"));

async function fetchFastApi(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.fastApiTimeoutMs);

  try {
    const response = await fetch(`${config.fastApiUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    return { response, body };
  } finally {
    clearTimeout(timeout);
  }
}

app.get("/api/health", async (_request, response) => {
  try {
    const result = await fetchFastApi("/api/health");
    response.status(result.response.ok ? 200 : 503).json({
      status: result.response.ok ? "ok" : "degraded",
      gateway: "online",
      fastapi: result.response.ok ? "online" : "unavailable",
      environment: config.nodeEnv,
      backend: result.body,
    });
  } catch (error) {
    const unavailable = error.name === "AbortError" || error instanceof TypeError;
    response.status(503).json({
      error: {
        code: unavailable ? "BACKEND_UNAVAILABLE" : "BACKEND_REQUEST_FAILED",
        message: "Risk service is temporarily unavailable.",
      },
    });
  }
});

app.use("/api", async (request, response) => {
  try {
    const query = request.originalUrl.includes("?")
      ? request.originalUrl.slice(request.originalUrl.indexOf("?"))
      : "";
    const path = `${request.path}${query}`;
    const result = await fetchFastApi(`/api${path}`, {
      method: request.method,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : JSON.stringify(request.body),
    });

    if (typeof result.body === "string") {
      response.status(result.response.status).send(result.body);
      return;
    }
    response.status(result.response.status).json(result.body);
  } catch (error) {
    const code = error.name === "AbortError"
      ? "BACKEND_TIMEOUT"
      : error instanceof TypeError
        ? "BACKEND_UNAVAILABLE"
        : "BACKEND_REQUEST_FAILED";
    response.status(code === "BACKEND_TIMEOUT" ? 504 : 503).json({
      error: {
        code,
        message: code === "BACKEND_TIMEOUT"
          ? "Risk service timed out."
          : "Risk service is temporarily unavailable.",
      },
    });
  }
});

app.use((error, _request, response, _next) => {
  if (error.message === "CORS origin is not allowed") {
    response.status(403).json({
      error: { code: "CORS_ORIGIN_NOT_ALLOWED", message: "Origin is not allowed." },
    });
    return;
  }
  response.status(500).json({
    error: { code: "GATEWAY_ERROR", message: "The API gateway encountered an error." },
  });
});

app.listen(config.port, () => {
  console.log(`LandslideGuard gateway listening on port ${config.port}`);
});
