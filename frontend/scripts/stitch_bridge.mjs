import { StitchError, StitchToolClient } from "@google/stitch-sdk";

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8").trim();
}

function getConfig() {
  const apiKey = process.env.STITCH_API_KEY || "";
  const accessToken = process.env.STITCH_ACCESS_TOKEN || "";
  const projectId = process.env.GOOGLE_CLOUD_PROJECT || "";
  const baseUrl = process.env.STITCH_HOST || process.env.STITCH_API_URL || undefined;

  return {
    apiKey: apiKey || undefined,
    accessToken: accessToken || undefined,
    projectId: projectId || undefined,
    baseUrl,
    timeout: 300_000,
  };
}

function serializeError(error) {
  if (error instanceof StitchError) {
    return {
      type: error.name,
      code: error.code,
      message: error.message,
      recoverable: error.recoverable,
      suggestion: error.suggestion || "",
    };
  }

  return {
    type: error?.name || "Error",
    code: "UNKNOWN_ERROR",
    message: error instanceof Error ? error.message : String(error),
    recoverable: false,
    suggestion: "",
  };
}

function formatConsoleArg(arg) {
  if (arg instanceof Error) {
    return arg.stack || `${arg.name}: ${arg.message}`;
  }
  if (typeof arg === "string") {
    return arg;
  }
  try {
    return JSON.stringify(arg);
  } catch {
    return String(arg);
  }
}

function normalizeError(error, transportLogs) {
  const serialized = serializeError(error);
  const combined = [serialized.message, ...transportLogs].join("\n").toLowerCase();

  if (
    combined.includes("und_err_socket") ||
    combined.includes("other side closed") ||
    combined.includes("server disconnected") ||
    combined.includes("fetch failed")
  ) {
    return {
      type: "StitchTransportError",
      code: "NETWORK_ERROR",
      message: "Stitch closed the connection before sending a response.",
      recoverable: true,
      suggestion: "",
    };
  }

  return serialized;
}

const toolName = process.argv[2];

if (!toolName) {
  console.error(JSON.stringify({
    ok: false,
    error: {
      type: "ValidationError",
      code: "VALIDATION_ERROR",
      message: "Missing Stitch tool name.",
      recoverable: false,
      suggestion: "",
    },
  }));
  process.exit(2);
}

let client;
const originalConsoleError = console.error;
const transportLogs = [];
console.error = (...args) => {
  transportLogs.push(args.map(formatConsoleArg).join(" "));
};

try {
  const rawInput = await readStdin();
  const argumentsPayload = rawInput ? JSON.parse(rawInput) : {};

  client = new StitchToolClient(getConfig());
  const result = await client.callTool(toolName, argumentsPayload);

  console.log(JSON.stringify({ ok: true, result }));
} catch (error) {
  originalConsoleError(JSON.stringify({ ok: false, error: normalizeError(error, transportLogs) }));
  process.exit(1);
} finally {
  console.error = originalConsoleError;
  if (client) {
    try {
      await client.close();
    } catch {
      // Ignore cleanup failures from the short-lived bridge process.
    }
  }
}
