import Constants from "expo-constants";
import * as LegacyFileSystem from "expo-file-system/legacy";
import { Platform } from "react-native";

export type Severity = "CRITICAL" | "MAJOR" | "WARNING";

export type ExtractedLabelData = {
  mrp: string | null;
  net_quantity: string | null;
  manufacturer_details: string | null;
  date_of_packing: string | null;
  country_of_origin: string | null;
  consumer_care: string | null;
  unit_sale_price: string | null;
  is_packaging_label?: boolean | null;
  image_assessment?: string | null;
};

export type Violation = {
  rule_id: string;
  field_name: string;
  severity: Severity;
  message: string;
  citation: string;
};

export type ScanResponse = {
  scan_id: string;
  status: "COMPLIANT" | "NON_COMPLIANT";
  overall_score: number;
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
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ScanApiError";
  }
}

// ---------------------------------------------------------------------------
// URL Resolution
// ---------------------------------------------------------------------------

function isLoopback(host: string): boolean {
  const h = host.trim().toLowerCase();
  return h === "localhost" || h === "127.0.0.1" || h === "::1" || h === "0.0.0.0";
}

function getApiBaseUrl(): string {
  // 1. Explicit env var (highest priority).
  //    Supports tunnels (ngrok / Cloudflare Tunnel) and production endpoints.
  //    On native devices we reject loopback values that would cause the phone
  //    to query itself instead of the PC.
  const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    const cleanUrl = configuredUrl.replace(/\/$/, "");
    const isLoopbackUrl =
      cleanUrl.includes("://localhost") || cleanUrl.includes("://127.0.0.1");

    if (Platform.OS !== "web" && isLoopbackUrl) {
      console.warn(
        "[API] EXPO_PUBLIC_API_URL is a loopback address — a physical device " +
          "cannot reach the PC via localhost. Falling through to dynamic detection."
      );
      // fall through to step 2
    } else {
      console.log("[API] Using EXPO_PUBLIC_API_URL:", cleanUrl);
      return cleanUrl;
    }
  }

  // 2. Dynamic LAN host from Expo Metro bundler.
  //    Expo Go sets debuggerHost / hostUri to the PC's actual LAN IP when the
  //    bundle is served over Wi-Fi. Loopback values are explicitly rejected.
  const metroHost =
    Constants.expoGoConfig?.debuggerHost ?? Constants.expoConfig?.hostUri;
  const host = metroHost?.split(":")[0]?.trim();

  if (host && !isLoopback(host)) {
    const derived = `http://${host}:8000/api/v1`;
    console.log("[API] Using Metro-derived host:", derived);
    return derived;
  }

  if (host) {
    console.warn(
      `[API] Metro host "${host}" is a loopback address — skipping. ` +
        "Set EXPO_PUBLIC_API_URL in .env to your PC's current Wi-Fi IP."
    );
  }

  // 3. Web browser: derive from window.location so the dev server and backend
  //    stay on the same host without any manual configuration.
  if (
    Platform.OS === "web" &&
    typeof window !== "undefined" &&
    window.location?.hostname &&
    !isLoopback(window.location.hostname)
  ) {
    return `http://${window.location.hostname}:8000/api/v1`;
  }

  // 4. Hard-coded LAN fallback — update EXPO_PUBLIC_API_URL in .env instead of
  //    changing this line. This is only reached when all dynamic methods fail.
  const fallback = Platform.OS === "web" ? "http://localhost:8000/api/v1" : "http://192.168.1.8:8000/api/v1";
  console.warn("[API] All dynamic discovery failed. Using hardcoded fallback:", fallback);
  return fallback;
}

// ---------------------------------------------------------------------------
// Image Upload
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

  console.log("================ [API DEBUG START] ================");
  console.log("[API] Target URL :", targetUrl);
  console.log("[API] Asset URI  :", asset.uri);
  console.log("[API] File name  :", fileName);
  console.log("[API] MIME type  :", mimeType);
  console.log("[API] Platform   :", Platform.OS);

  if (!asset?.uri) {
    console.error("[API] CRITICAL: asset.uri is undefined or null");
    throw new ScanApiError("No image URI provided to analyzeLabelImage.");
  }

  // ── WEB PATH ─────────────────────────────────────────────────────────────
  // Browsers handle multipart/form-data correctly through the native Fetch API.
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

    let response: Response;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60_000);
    try {
      response = await fetch(targetUrl, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });
    } catch (err: any) {
      throw new ScanApiError(
        `Could not reach Label Police (${err?.message ?? "Network Error"}). ` +
          "Check your network connection."
      );
    } finally {
      clearTimeout(timeout);
      console.log("================ [API DEBUG END] ================");
    }

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload?.detail;
      const message = typeof detail === "string" ? detail : detail?.message;
      throw new ScanApiError(
        message || "The label could not be analyzed.",
        response.status
      );
    }
    return payload as ScanResponse;
  }

  // ── NATIVE PATH (Android / iOS) ───────────────────────────────────────────
  // React Native's JS fetch polyfill throws "Unsupported FormDataPart
  // implementation" when a plain JS object is passed to FormData on the native
  // bridge.
  //
  // LegacyFileSystem.uploadAsync reads the file directly from the native file
  // system and builds the multipart body entirely in native code, so the JS
  // bridge never encounters a FormDataPart at all.
  let uploadResult: LegacyFileSystem.FileSystemUploadResult;
  try {
    console.log("[API] Using LegacyFileSystem.uploadAsync (native path)");
    uploadResult = await LegacyFileSystem.uploadAsync(targetUrl, asset.uri, {
      httpMethod: "POST",
      uploadType: LegacyFileSystem.FileSystemUploadType.MULTIPART,
      fieldName: "file",
      mimeType,
      // Do NOT set Content-Type here — the native layer must generate the
      // multipart boundary automatically, exactly as browsers do.
    });
  } catch (err: any) {
    console.error("[API] LegacyFileSystem.uploadAsync FAILED:");
    console.error("[API] Error Message:", err?.message);
    console.error("[API] Error Stack  :", err?.stack);
    throw new ScanApiError(
      `Could not reach Label Police (${err?.message ?? "Network Error"}). ` +
        "Make sure the backend is running and your phone is on the same Wi-Fi network."
    );
  } finally {
    console.log("================ [API DEBUG END] ================");
  }

  console.log("[API] uploadAsync HTTP status:", uploadResult.status);

  // uploadAsync returns the raw body as a string — parse it manually.
  let payload: any = null;
  try {
    payload = JSON.parse(uploadResult.body);
  } catch {
    // Leave payload as null; the status check below will surface the error.
  }

  if (uploadResult.status < 200 || uploadResult.status >= 300) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new ScanApiError(
      message || "The label could not be analyzed.",
      uploadResult.status
    );
  }

  return payload as ScanResponse;
}

// ---------------------------------------------------------------------------
// Scan History
// ---------------------------------------------------------------------------

export async function fetchScanHistory(): Promise<ScanHistoryItem[]> {
  const baseUrl = getApiBaseUrl();
  const targetUrl = `${baseUrl}/scans`;

  console.log("================ [HISTORY API DEBUG] ================");
  console.log("[API] Target URL:", targetUrl);

  let response: Response;
  try {
    response = await fetch(targetUrl);
    console.log("[API] History response status:", response.status);
  } catch (err: any) {
    console.error("[API] HISTORY FETCH FAILED:");
    console.error("[API] Error Message:", err?.message);
    console.error("[API] Error Stack  :", err?.stack);
    throw new ScanApiError(
      `Could not reach Label Police (${err?.message ?? "Network Error"}). ` +
        "Start the backend and ensure this device can reach it over your local network."
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message;
    throw new ScanApiError(
      message || "Your scan history could not be loaded.",
      response.status
    );
  }
  return Array.isArray(payload) ? (payload as ScanHistoryItem[]) : [];
}
