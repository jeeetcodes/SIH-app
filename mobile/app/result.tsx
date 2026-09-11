import { useMemo, type FC } from "react";
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import type { ScanResponse } from "@/services/scan-api";

const COLORS = {
  navy: "#1B365D",
  offWhite: "#F8FAFC",
  card: "#FFFFFF",
  text: "#0F172A",
  muted: "#64748B",
  border: "#E2E8F0",
  greenBg: "#DCFCE7",
  greenText: "#15803D",
  redBg: "#FEE2E2",
  redText: "#B91C1C",
  amberBg: "#FEF3C7",
  amberText: "#B45309",
} as const;

function parseReport(value?: string | string[]): ScanResponse | null {
  try {
    const text = Array.isArray(value) ? value[0] : value;
    return text ? (JSON.parse(text) as ScanResponse) : null;
  } catch {
    return null;
  }
}

const Result: FC = () => {
  const router = useRouter();
  const params = useLocalSearchParams<{ imageUri?: string | string[]; report?: string | string[] }>();
  const imageUri = Array.isArray(params.imageUri) ? params.imageUri[0] : params.imageUri;
  const report = useMemo(() => parseReport(params.report), [params.report]);

  if (!report) {
    return (
      <View style={styles.centered}>
        <Text style={styles.title}>No inspection result available</Text>
        <Text style={styles.body}>Please return and scan a package label again.</Text>
        <Pressable onPress={() => router.replace("/(tabs)")} style={styles.button}>
          <Text style={styles.buttonText}>Return to Scanner</Text>
        </Pressable>
      </View>
    );
  }

  const compliant = report.status === "COMPLIANT";

  return (
    <View style={styles.root}>
      <Stack.Screen
        options={{
          headerShown: true,
          title: "Inspection Result",
          headerStyle: { backgroundColor: COLORS.navy },
          headerTintColor: "#FFFFFF",
          headerTitleStyle: { fontWeight: "700" },
        }}
      />

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* Label Image Thumbnail */}
        {imageUri ? (
          <View style={styles.thumbContainer}>
            <Image source={{ uri: imageUri }} style={styles.thumb} resizeMode="contain" />
          </View>
        ) : null}

        {/* Status Badge & Score Header */}
        <View style={[styles.scoreCard, compliant ? styles.compliantCard : styles.nonCompliantCard]}>
          <View style={styles.badgeRow}>
            <Text style={[styles.badge, compliant ? styles.compliantBadge : styles.nonCompliantBadge]}>
              {compliant ? "🟢 COMPLIANT" : "🔴 NON-COMPLIANT"}
            </Text>
            <Text style={styles.scoreText}>{report.overall_score} / 100</Text>
          </View>

          <Text style={[styles.statusText, compliant ? styles.compliantText : styles.nonCompliantText]}>
            {compliant
              ? "All Legal Metrology Rule 6 Declarations Validated"
              : "Rule Violations Detected — Requires Remediation"}
          </Text>
        </View>

        {report.used_mock_vision ? (
          <View style={styles.notice}>
            <Text style={styles.noticeTitle}>Demo Fixture Mode</Text>
            <Text style={styles.noticeText}>
              Configure a GEMINI_API_KEY in backend/.env for live AI image extraction.
            </Text>
          </View>
        ) : null}

        {/* Extracted Declarations Cards */}
        <Text style={styles.sectionTitle}>Extracted Package Declarations</Text>
        <View style={styles.dataCard}>
          <Field label="Maximum Retail Price (MRP)" value={report.extracted_data.mrp} />
          <Field label="Net Quantity / Net Mass" value={report.extracted_data.net_quantity} />
          <Field label="Date of Mfg / Packing" value={report.extracted_data.date_of_packing} />
          <Field label="Manufacturer / Importer Details" value={report.extracted_data.manufacturer_details} />
          <Field label="Country of Origin" value={report.extracted_data.country_of_origin} />
          <Field label="Consumer Care Contact" value={report.extracted_data.consumer_care} />
          <Field label="Unit Sale Price" value={report.extracted_data.unit_sale_price} />
        </View>

        {/* Compliance Findings & Violations */}
        <Text style={styles.sectionTitle}>Compliance Findings ({report.violations.length})</Text>
        {report.violations.length === 0 ? (
          <View style={styles.okCard}>
            <Text style={styles.okIcon}>✅</Text>
            <Text style={styles.okText}>No Rule 6 violations detected. Label meets standards.</Text>
          </View>
        ) : (
          report.violations.map((violation, index) => (
            <View key={`${violation.rule_id}-${index}`} style={styles.violationCard}>
              <View style={styles.violationHeader}>
                <Text style={violation.severity === "CRITICAL" ? styles.criticalTag : styles.warningTag}>
                  {violation.severity === "CRITICAL"
                    ? "🔴 CRITICAL"
                    : violation.severity === "MAJOR"
                      ? "🟠 MAJOR"
                      : "⚠️ WARNING"}
                </Text>
                <Text style={styles.ruleId}>{violation.rule_id}</Text>
              </View>
              <Text style={styles.violationMessage}>{violation.message}</Text>
              <Text style={styles.citation}>Clause: {violation.citation}</Text>
            </View>
          ))
        )}

        {/* Scan Another Button */}
        <Pressable onPress={() => router.replace("/(tabs)")} style={styles.button}>
          <Text style={styles.buttonText}>📷 Scan Another Product Label</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
};

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={[styles.fieldValue, !value && styles.missingValue]}>
        {value || "Not Detected / Missing"}
      </Text>
    </View>
  );
}

export default Result;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.offWhite },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  centered: { flex: 1, padding: 24, justifyContent: "center", backgroundColor: COLORS.offWhite },

  thumbContainer: { borderRadius: 12, overflow: "hidden", borderBottomWidth: 1, borderColor: COLORS.border },
  thumb: { width: "100%", height: 400, maxHeight: 400, backgroundColor: "#CBD5E1" },

  scoreCard: { borderRadius: 16, padding: 18, borderWidth: 1 },
  compliantCard: { backgroundColor: COLORS.greenBg, borderColor: "#BBF7D0" },
  nonCompliantCard: { backgroundColor: COLORS.redBg, borderColor: "#FECACA" },
  badgeRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  badge: { fontSize: 13, fontWeight: "800", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  compliantBadge: { backgroundColor: "#DCFCE7", color: COLORS.greenText },
  nonCompliantBadge: { backgroundColor: "#FEE2E2", color: COLORS.redText },
  scoreText: { fontSize: 24, fontWeight: "800", color: COLORS.text },
  statusText: { marginTop: 10, fontSize: 15, fontWeight: "700", lineHeight: 20 },
  compliantText: { color: COLORS.greenText },
  nonCompliantText: { color: COLORS.redText },

  sectionTitle: { fontSize: 17, fontWeight: "800", color: COLORS.navy, marginTop: 6 },
  dataCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingHorizontal: 16,
  },
  field: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  fieldLabel: { fontSize: 11, fontWeight: "800", color: COLORS.muted, textTransform: "uppercase" },
  fieldValue: { marginTop: 4, fontSize: 15, lineHeight: 20, color: COLORS.text, fontWeight: "500" },
  missingValue: { color: "#94A3B8", fontStyle: "italic" },

  okCard: {
    backgroundColor: COLORS.greenBg,
    borderRadius: 12,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  okIcon: { fontSize: 20 },
  okText: { color: COLORS.greenText, fontWeight: "700", fontSize: 14, flex: 1 },

  violationCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 16,
    gap: 6,
  },
  violationHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  criticalTag: { color: COLORS.redText, fontSize: 12, fontWeight: "800" },
  warningTag: { color: COLORS.amberText, fontSize: 12, fontWeight: "800" },
  ruleId: { fontSize: 12, fontWeight: "700", color: COLORS.muted },
  violationMessage: { color: COLORS.text, fontSize: 15, fontWeight: "600", lineHeight: 21 },
  citation: { color: COLORS.muted, fontSize: 12 },

  notice: { backgroundColor: COLORS.amberBg, borderRadius: 12, padding: 14 },
  noticeTitle: { color: COLORS.amberText, fontWeight: "800", fontSize: 13 },
  noticeText: { color: COLORS.text, marginTop: 4, fontSize: 13, lineHeight: 18 },

  title: { fontSize: 22, fontWeight: "700", color: COLORS.navy },
  body: { fontSize: 15, lineHeight: 22, color: COLORS.muted },
  button: {
    backgroundColor: COLORS.navy,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
});
