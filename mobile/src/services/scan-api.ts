import Constants from "expo-constants";
import * as LegacyFileSystem from "expo-file-system/legacy";
import { Platform } from "react-native";

export type Severity = "CRITICAL" | "MAJOR" | "MINOR" | "WARNING" | "critical" | "major" | "minor";

export type ExtractedLabelData = {
  product_name?: string | null;
  product_category?: string | null;
  mrp: string | null;
  net_quantity: string | null;
  manufacturer_details: string | null;
  date_of_packing: string | null;
  expiry_date?: string | null;
  country_of_origin: string | null;
  consumer_care: string | null;
  unit_sale_price: string | null;
  fssai_license?: string | null;
  ingredients?: string | null;
  formatting_assessment?: string | null;
  is_packaging_label?: boolean | null;
  image_assessment?: string | null;
};

export type Violation = {
  rule_id: string;
  rule_name?: string;
  field_name: string;
  severity: Severity;
  penalty?: number;
  message: string;
  explanation?: string;
  citation: string;
};

export type ScanResponse = {
  scan_id: string;
  status: "COMPLIANT" | "NON_COMPLIANT";
  final_score?: number;
  overall_score: number;
  product_category?: string | null;
  extracted_data: ExtractedLabelData;
  violations: Violation[];
  used_mock_vision: boolean;
  is_packaging_label?: boolean | null;
  image_assessment?: string | null;
};

export type ScanHistoryItem = {
  id: number;
  created_at: string;
  product_name: string | null;
  score: number;
  is_compliant: boolean;
};

export class ScanApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly code?: string) {
    super(message);
    this.name = "ScanApiError";
  }
}

// ---------------------------------------------------------------------------
// Constants & Configuration
// ---------------------------------------------------------------------------

export const PRODUCTION_API_URL = "https://packlens-3ko8.onrender.com/api/v1";
export const REQUEST_TIMEOUT_MS = 120_000; // 120s timeout to support Render free tier cold starts
export const RETRY_DELAY_MS = 5_000; // 5s wait before retry on transient network/timeout failure
export const COLD_START_MESSAGE =
  "Server is spinning up (Render free tier cold start). Please wait ~30 seconds and try again.";

// ---------------------------------------------------------------------------
// URL Resolution & Sanitization
// ---------------------------------------------------------------------------

function isLoopback(host: string): boolean {
  const h = host.trim().toLowerCase();
  return h === "localhost" || h === "127.0.0.1" || h === "::1" || h === "0.0.0.0";
}

function sanitizeUrl(rawUrl: string): string {
  let url = rawUrl.trim();
  // Fix accidental duplicate schemes like https://https:// or http://http://
  url = url.replace(/^(https?:\/\/)+/i, (match) => {
    return match.toLowerCase().startsWith("https") ? "https://" : "http://";
  });
  // Strip trailing slashes
  return url.replace(/\/+$/, "");
}

export function getApiBaseUrl(): string {
  // 1. Explicit env var (highest priority).
  const rawEnvUrl = process.env.EXPO_PUBLIC_API_URL;
  if (rawEnvUrl && rawEnvUrl.trim().length > 0) {
    const cleanUrl = sanitizeUrl(rawEnvUrl);
    const isLoopbackUrl =
      cleanUrl.includes("://localhost") ||
      cleanUrl.includes("://127.0.0.1") ||
      cleanUrl.includes("://0.0.0.0");

    if (Platform.OS !== "web" && isLoopbackUrl) {
      console.warn(
        "[API] EXPO_PUBLIC_API_URL points to localhost, which is unreachable from physical mobile devices. Falling back to production Render backend."
      );
      return PRODUCTION_API_URL;
    }
    console.log("[API] Using EXPO_PUBLIC_API_URL:", cleanUrl);
    return cleanUrl;
  }

  // 2. Dynamic LAN host from Expo Metro bundler (if available during local Wi-Fi development).
  const metroHost =
    Constants.expoGoConfig?.debuggerHost ?? Constants.expoConfig?.hostUri;
  const host = metroHost?.split(":")[0]?.trim();

  if (host && !isLoopback(host)) {
    const derived = `http://${host}:8000/api/v1`;
    console.log("[API] Using Metro-derived local host:", derived);
    return derived;
  }

  // 3. Web browser location host if applicable
  if (
    Platform.OS === "web" &&
    typeof window !== "undefined" &&
    window.location?.hostname &&
    !isLoopback(window.location.hostname)
  ) {
    return `http://${window.location.hostname}:8000/api/v1`;
  }

  // 4. Robust production fallback to live Render backend
  console.log("[API] Defaulting to production Render API URL:", PRODUCTION_API_URL);
  return PRODUCTION_API_URL;
}

// ---------------------------------------------------------------------------
// Error & Timeout Helpers
// ---------------------------------------------------------------------------

function isColdStartOrTimeoutError(error: any): boolean {
  if (!error) return false;
  const message = (error.message || "").toLowerCase();
  const code = (error.code || "").toUpperCase();
  const status = error.status;

  return (
    code === "ECONNABORTED" ||
    code === "ETIMEDOUT" ||
    code === "ERR_NETWORK" ||
    code === "ENOTFOUND" ||
    code === "ECONNREFUSED" ||
    message.includes("timeout") ||
    message.includes("timed out") ||
    message.includes("aborted") ||
    message.includes("failed to connect") ||
    message.includes("network request failed") ||
    message.includes("network error") ||
    message.includes("cold start") ||
    message.includes("504") ||
    status === 504 ||
    status === 502 ||
    status === 503
  );
}

function handleApiError(error: any, fallbackMessage: string): ScanApiError {
  if (error instanceof ScanApiError) {
    if (isColdStartOrTimeoutError(error) && !error.message.includes("spinning up")) {
      return new ScanApiError(COLD_START_MESSAGE, error.status, "ECONNABORTED");
    }
    return error;
  }

  if (isColdStartOrTimeoutError(error)) {
    return new ScanApiError(COLD_START_MESSAGE, error?.status, "ECONNABORTED");
  }

  const message = error?.message || fallbackMessage;
  return new ScanApiError(message, error?.status, error?.code);
}

// ---------------------------------------------------------------------------
// Backend Warm-up (Health Ping)
// ---------------------------------------------------------------------------

/**
 * Sends a lightweight GET ping to /api/v1/health to wake up the Render free-tier
 * backend early when the app boots or mounts.
 */
export async function pingBackend(timeoutMs = 15_000): Promise<boolean> {
  const baseUrl = getApiBaseUrl();
  const healthUrl = `${baseUrl}/health`;
  console.log("[API] Pinging backend to warm up:", healthUrl);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(healthUrl, {
      method: "GET",
      signal: controller.signal,
    });
    console.log("[API] Warm-up ping response status:", response.status);
    return response.ok;
  } catch (err: any) {
    console.warn("[API] Ping attempt non-fatal result (server waking up):", err?.message);
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Internal Network Request Helpers with 120s Timeout
// ---------------------------------------------------------------------------

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } catch (err: any) {
    if (err?.name === "AbortError") {
      const timeoutErr: any = new Error(`Request timed out after ${timeoutMs}ms`);
      timeoutErr.code = "ECONNABORTED";
      throw timeoutErr;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function uploadAsyncWithTimeout(
  targetUrl: string,
  fileUri: string,
  mimeType: string,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<LegacyFileSystem.FileSystemUploadResult> {
  let timer: any;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      const err: any = new Error(`Upload timed out after ${timeoutMs}ms`);
      err.code = "ECONNABORTED";
      reject(err);
    }, timeoutMs);
  });

  try {
    const uploadPromise = LegacyFileSystem.uploadAsync(targetUrl, fileUri, {
      httpMethod: "POST",
      uploadType: LegacyFileSystem.FileSystemUploadType.MULTIPART,
      fieldName: "file",
      mimeType,
    });

    return await Promise.race([uploadPromise, timeoutPromise]);
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Image Upload & Analysis (with 120s Timeout & Auto-Retry)
// ---------------------------------------------------------------------------

export async function analyzeLabelImage(asset: {
  uri: string;
  fileName?: string | null;
  mimeType?: string | null;
}): Promise<ScanResponse> {
  const baseUrl = getApiBaseUrl();
  const targetUrl = `${baseUrl}/scans/analyze`;
  const fileName = asset.fileName || `label_${Date.now()}.jpg`;
  const mimeType = asset.mimeType || "image/jpeg";

  console.log("================ [API SCAN REQUEST] ================");
  console.log("[API] Target URL :", targetUrl);
  console.log("[API] Asset URI  :", asset.uri);
  console.log("[API] File name  :", fileName);
  console.log("[API] MIME type  :", mimeType);
  console.log("[API] Platform   :", Platform.OS);

  if (!asset?.uri) {
    console.error("[API] CRITICAL: asset.uri is undefined or null");
    throw new ScanApiError("No image URI provided to analyzeLabelImage.");
  }

  const maxAttempts = 2;
  let lastError: any = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      console.log(`[API] Processing analysis attempt ${attempt}/${maxAttempts}`);

      if (Platform.OS === "web") {
        let imageBlob: Blob;
        try {
          const res = await fetch(asset.uri);
          imageBlob = await res.blob();
        } catch {
          throw new ScanApiError(
            "The selected image could not be read by the browser. Please choose it again."
          );
        }

        const formData = new FormData();
        formData.append("file", imageBlob, fileName);

        const response = await fetchWithTimeout(targetUrl, {
          method: "POST",
          body: formData,
        }, REQUEST_TIMEOUT_MS);

        const payload = await response.json().catch(() => null);

        if (!response.ok) {
          console.error("[API] Backend Error Details (web):", response.status, JSON.stringify(payload));

          if (response.status === 504 && attempt < maxAttempts) {
            console.warn(`[API] 504 Gateway Timeout on attempt ${attempt}. Retrying in ${RETRY_DELAY_MS}ms...`);
            await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
            continue;
          }

          const detail = payload?.detail;
          const message = typeof detail === "string"
            ? detail
            : typeof detail === "object" && detail?.message
              ? detail.message
              : null;
          throw new ScanApiError(
            message || `Server responded with ${response.status}. The label could not be analyzed.`,
            response.status
          );
        }

        console.log("[API] Scan analysis completed successfully on web.");
        return payload as ScanResponse;
      } else {
        // Native path (iOS / Android) using LegacyFileSystem.uploadAsync
        const uploadResult = await uploadAsyncWithTimeout(
          targetUrl,
          asset.uri,
          mimeType,
          REQUEST_TIMEOUT_MS
        );

        console.log(`[API] uploadAsync attempt ${attempt} HTTP status:`, uploadResult.status);
        console.log(`[API] uploadAsync response body preview:`, uploadResult.body?.substring(0, 500));

        let payload: any = null;
        try {
          payload = JSON.parse(uploadResult.body);
        } catch {
          // Leave payload as null if body isn't JSON
        }

        if (uploadResult.status < 200 || uploadResult.status >= 300) {
          console.error(
            "[API] Backend Error Details (native):",
            uploadResult.status,
            JSON.stringify(payload)
          );

          if (uploadResult.status === 504 && attempt < maxAttempts) {
            console.warn(`[API] 504 Gateway Timeout on attempt ${attempt}. Retrying in ${RETRY_DELAY_MS}ms...`);
            await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
            continue;
          }

          const detail = payload?.detail;
          const message = typeof detail === "string"
            ? detail
            : typeof detail === "object" && detail?.message
              ? detail.message
              : Array.isArray(detail)
                ? detail.map((d: any) => d?.msg || d?.message || JSON.stringify(d)).join("; ")
                : null;
          throw new ScanApiError(
            message || `Server responded with ${uploadResult.status}. The label could not be analyzed.`,
            uploadResult.status
          );
        }

        console.log("[API] Scan analysis completed successfully on native.");
        return payload as ScanResponse;
      }
    } catch (err: any) {
      lastError = err;
      console.error(
        `[API] Attempt ${attempt}/${maxAttempts} FAILED.`,
        "\n  Error name   :", err?.name,
        "\n  Error message:", err?.message,
        "\n  Error code   :", err?.code,
        "\n  HTTP status  :", err?.status,
        "\n  Stack        :", err?.stack?.split("\n").slice(0, 3).join("\n")
      );

      if (attempt < maxAttempts && isColdStartOrTimeoutError(err)) {
        console.log(`[API] Cold-start/timeout detected on attempt ${attempt}. Retrying in ${RETRY_DELAY_MS}ms...`);
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }

      // Non-retryable error (e.g. 400, 422, 500) — break immediately
      break;
    }
  }

  console.error(
    "[API] All analyze attempts exhausted. Last error:",
    lastError?.name, lastError?.message, "status:", lastError?.status
  );
  throw handleApiError(lastError, "Could not reach Label Police. Check your network connection.");
}

// ---------------------------------------------------------------------------
// Scan History (with 120s Timeout & Auto-Retry)
// ---------------------------------------------------------------------------

export async function fetchScanHistory(): Promise<ScanHistoryItem[]> {
  const baseUrl = getApiBaseUrl();
  const targetUrl = `${baseUrl}/scans`;

  console.log("================ [HISTORY API DEBUG] ================");
  console.log("[API] Target URL:", targetUrl);

  const maxAttempts = 2;
  let lastError: any = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      console.log(`[API] Fetching scan history (attempt ${attempt}/${maxAttempts})`);
      const response = await fetchWithTimeout(targetUrl, { method: "GET" }, REQUEST_TIMEOUT_MS);
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 504 && attempt < maxAttempts) {
          console.warn(`[API] 504 on history fetch. Retrying in ${RETRY_DELAY_MS}ms...`);
          await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
          continue;
        }

        const detail = payload?.detail;
        const message = typeof detail === "string" ? detail : detail?.message;
        throw new ScanApiError(
          message || "Your scan history could not be loaded.",
          response.status
        );
      }

      return Array.isArray(payload) ? (payload as ScanHistoryItem[]) : [];
    } catch (err: any) {
      lastError = err;
      console.warn(`[API] History fetch attempt ${attempt} failed:`, err?.message);

      if (attempt < maxAttempts && isColdStartOrTimeoutError(err)) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }

      break;
    }
  }

  throw handleApiError(lastError, "Your scan history could not be loaded.");
}
