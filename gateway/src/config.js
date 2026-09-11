import "dotenv/config";

function csv(value, fallback) {
  return (value || fallback)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

const port = Number.parseInt(process.env.PORT || "3000", 10);
const timeoutMs = Number.parseInt(process.env.FASTAPI_TIMEOUT_MS || "15000", 10);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("PORT must be a valid TCP port");
}

if (!Number.isInteger(timeoutMs) || timeoutMs < 1000) {
  throw new Error("FASTAPI_TIMEOUT_MS must be at least 1000 milliseconds");
}

export const config = {
  port,
  nodeEnv: process.env.NODE_ENV || "development",
  fastApiUrl: (process.env.FASTAPI_URL || "http://localhost:8000").replace(/\/+$/, ""),
  corsOrigins: csv(process.env.CORS_ORIGINS, "http://localhost:5173"),
  fastApiTimeoutMs: timeoutMs,
};
