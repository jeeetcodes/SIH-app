import React, { useMemo } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import type { ScanResponse, Violation } from "@/services/scan-api";

const COLORS = {
  navy: "#1B365D",
  navyMuted: "#2C4A6E",
  offWhite: "#F8FAFC",
  card: "#FFFFFF",
  text: "#0F172A",
  muted: "#64748B",
  border: "#E2E8F0",
  greenBg: "#DCFCE7",
  greenBorder: "#BBF7D0",
  greenText: "#15803D",
  amberBg: "#FEF3C7",
  amberBorder: "#FDE68A",
  amberText: "#B45309",
  orangeBg: "#FFEDD5",
  orangeBorder: "#FED7AA",
  orangeText: "#C2410C",
  redBg: "#FEE2E2",
  redBorder: "#FECACA",
  redText: "#B91C1C",
  categoryBg: "#EEF2FF",
  categoryText: "#4338CA",
  categoryBorder: "#C7D2FE",
} as const;

interface InspectionResultViewProps {
  imageUri?: string | null;
  report: ScanResponse;
  onScanAgain?: () => void;
}

function getCategoryIcon(category?: string | null): string {
  if (!category) return "🏷️";
  const cat = category.toLowerCase();
  if (cat.includes("food") || cat.includes("beverage")) return "🍔";
  if (cat.includes("cosmetic")) return "💄";
  if (cat.includes("electronic")) return "⚡";
  if (cat.includes("grocery")) return "🛒";
  if (cat.includes("medical") || cat.includes("fmcg")) return "💊";
  return "📦";
}

function normalizeSeverity(severity: string): "CRITICAL" | "MAJOR" | "MINOR" {
  const s = (severity || "").toUpperCase();
  if (s === "CRITICAL") return "CRITICAL";
  if (s === "MAJOR") return "MAJOR";
  return "MINOR";
}

export const InspectionResultView: React.FC<InspectionResultViewProps> = ({
  imageUri,
  report,
  onScanAgain,
}) => {
  const safeImageUri = useMemo(() => {
    if (!imageUri) return null;
    try {
      return decodeURIComponent(imageUri);
    } catch {
      return imageUri;
    }
  }, [imageUri]);

  const score = report.final_score ?? report.overall_score;
  const compliant = report.status === "COMPLIANT";

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}>
      {/* Category Header Badge */}
      {report.product_category ? (
        <View style={styles.categoryBadge}>
          <Text style={styles.categoryIcon}>
            {getCategoryIcon(report.product_category)}
          </Text>
          <Text style={styles.categoryText}>
            CATEGORY: {report.product_category.toUpperCase()}
          </Text>
        </View>
      ) : null}

      {/* Captured Image Display */}
      {safeImageUri ? (
        <View style={styles.imageCard}>
          <View style={styles.imageHeader}>
            <Text style={styles.imageTag}>INSPECTED LABEL PHOTO</Text>
          </View>
          <Image
            source={{ uri: safeImageUri }}
            style={styles.imagePreview}
            contentFit="contain"
            transition={200}
            accessibilityLabel="Inspected packaging label"
          />
        </View>
      ) : null}

      {/* Overall Score & Compliance Banner */}
      <View
        style={[
          styles.scoreCard,
          compliant ? styles.compliantCard : styles.nonCompliantCard,
        ]}>
        <View style={styles.scoreRow}>
          <View
            style={[
              styles.statusBadge,
              compliant ? styles.statusBadgeCompliant : styles.statusBadgeNonCompliant,
            ]}>
            <Text
              style={[
                styles.statusBadgeText,
                compliant ? styles.compliantText : styles.nonCompliantText,
              ]}>
              {compliant ? "🟢 COMPLIANT" : "🔴 NON-COMPLIANT"}
            </Text>
          </View>
          <View style={styles.scoreNumberContainer}>
            <Text style={styles.scoreNumber}>{score}</Text>
            <Text style={styles.scoreTotal}>/ 100</Text>
          </View>
        </View>

        <Text
          style={[
            styles.statusDescription,
            compliant ? styles.compliantText : styles.nonCompliantText,
          ]}>
          {compliant
            ? "All Legal Metrology (Packaged Commodities) Rule 6 declarations validated."
            : "Rule violations detected. Penalties applied based on Legal Metrology Rules, 2011."}
        </Text>
      </View>

      {/* Demo Fixture Notice if mock was used */}
      {report.used_mock_vision ? (
        <View style={styles.noticeCard}>
          <Text style={styles.noticeTitle}>Demo Fixture Mode</Text>
          <Text style={styles.noticeText}>
            Configure a GEMINI_API_KEY in backend/.env for live AI image extraction.
          </Text>
        </View>
      ) : null}

      {/* Extracted Package Declarations */}
      <Text style={styles.sectionTitle}>Extracted Package Declarations</Text>
      <View style={styles.dataCard}>
        {report.extracted_data.product_name ? (
          <DeclarationRow
            label="Product Name"
            value={report.extracted_data.product_name}
          />
        ) : null}
        <DeclarationRow
          label="Maximum Retail Price (MRP)"
          value={report.extracted_data.mrp}
        />
        <DeclarationRow
          label="Net Quantity / Content"
          value={report.extracted_data.net_quantity}
        />
        <DeclarationRow
          label="Date of Mfg / Packing"
          value={report.extracted_data.date_of_packing}
        />
        {report.extracted_data.expiry_date ? (
          <DeclarationRow
            label="Expiry / Best Before Date"
            value={report.extracted_data.expiry_date}
          />
        ) : null}
        {report.extracted_data.fssai_license ? (
          <DeclarationRow
            label="FSSAI License Number"
            value={report.extracted_data.fssai_license}
          />
        ) : null}
        {report.extracted_data.ingredients ? (
          <DeclarationRow
            label="Ingredients / Composition"
            value={report.extracted_data.ingredients}
          />
        ) : null}
        <DeclarationRow
          label="Manufacturer / Packer Details"
          value={report.extracted_data.manufacturer_details}
        />
        <DeclarationRow
          label="Country of Origin"
          value={report.extracted_data.country_of_origin}
        />
        <DeclarationRow
          label="Consumer Care Contact"
          value={report.extracted_data.consumer_care}
        />
        <DeclarationRow
          label="Unit Sale Price"
          value={report.extracted_data.unit_sale_price}
        />
      </View>

      {/* Compliance Findings & Violations */}
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>
          Compliance Findings ({report.violations.length})
        </Text>
      </View>

      {report.violations.length === 0 ? (
        <View style={styles.compliantNotice}>
          <Text style={styles.compliantNoticeIcon}>✅</Text>
          <Text style={styles.compliantNoticeText}>
            No Legal Metrology violations detected. All declarations conform to
            the Packaged Commodities Rules, 2011.
          </Text>
        </View>
      ) : (
        report.violations.map((violation, index) => (
          <ViolationCard
            key={`${violation.rule_id}-${index}`}
            violation={violation}
          />
        ))
      )}

      {/* Scan Another Button */}
      {onScanAgain ? (
        <Pressable
          onPress={onScanAgain}
          style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}>
          <Text style={styles.actionButtonText}>📷 Scan Another Product Label</Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
};

function ViolationCard({ violation }: { violation: Violation }) {
  const norm = normalizeSeverity(violation.severity);
  const penalty = violation.penalty ?? (norm === "CRITICAL" ? 25 : norm === "MAJOR" ? 15 : 5);

  const cardStyle =
    norm === "CRITICAL"
      ? styles.violationCritical
      : norm === "MAJOR"
      ? styles.violationMajor
      : styles.violationMinor;

  const tagStyle =
    norm === "CRITICAL"
      ? styles.tagCritical
      : norm === "MAJOR"
      ? styles.tagMajor
      : styles.tagMinor;

  const penaltyStyle =
    norm === "CRITICAL"
      ? styles.penaltyCritical
      : norm === "MAJOR"
      ? styles.penaltyMajor
      : styles.penaltyMinor;

  return (
    <View style={[styles.violationCard, cardStyle]}>
      <View style={styles.violationHeader}>
        <View style={[styles.severityTag, tagStyle]}>
          <Text style={styles.severityTagText}>
            {norm === "CRITICAL"
              ? "🔴 CRITICAL"
              : norm === "MAJOR"
              ? "🟠 MAJOR"
              : "⚠️ MINOR"}
          </Text>
        </View>
        <View style={[styles.penaltyBadge, penaltyStyle]}>
          <Text style={styles.penaltyText}>-{penalty} PTS</Text>
        </View>
      </View>

      <Text style={styles.violationRuleName}>
        {violation.rule_name || violation.rule_id}
      </Text>

      <Text style={styles.violationMessage}>
        {violation.explanation || violation.message}
      </Text>

      <View style={styles.citationContainer}>
        <Text style={styles.citationLabel}>Clause:</Text>
        <Text style={styles.citationText}>{violation.citation}</Text>
      </View>
    </View>
  );
}

function DeclarationRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <View style={styles.fieldRow}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={[styles.fieldValue, !value && styles.missingValue]}>
        {value || "Not Detected / Missing"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 16,
    gap: 16,
    paddingBottom: 40,
  },
  categoryBadge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    backgroundColor: COLORS.categoryBg,
    borderColor: COLORS.categoryBorder,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 6,
  },
  categoryIcon: { fontSize: 16 },
  categoryText: {
    fontSize: 12,
    fontWeight: "800",
    color: COLORS.categoryText,
    letterSpacing: 0.5,
  },

  imageCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 12,
    gap: 8,
  },
  imageHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 4,
  },
  imageTag: {
    fontSize: 11,
    fontWeight: "800",
    color: COLORS.navy,
    letterSpacing: 0.8,
  },
  imagePreview: {
    width: "100%",
    height: 360,
    borderRadius: 12,
    backgroundColor: "#F1F5F9",
  },

  scoreCard: {
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
  },
  compliantCard: {
    backgroundColor: COLORS.greenBg,
    borderColor: COLORS.greenBorder,
  },
  nonCompliantCard: {
    backgroundColor: COLORS.redBg,
    borderColor: COLORS.redBorder,
  },
  scoreRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  statusBadge: {
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statusBadgeCompliant: { backgroundColor: "#FFFFFF" },
  statusBadgeNonCompliant: { backgroundColor: "#FFFFFF" },
  statusBadgeText: { fontSize: 13, fontWeight: "800" },
  compliantText: { color: COLORS.greenText },
  nonCompliantText: { color: COLORS.redText },
  scoreNumberContainer: { flexDirection: "row", alignItems: "baseline" },
  scoreNumber: { fontSize: 28, fontWeight: "900", color: COLORS.text },
  scoreTotal: { fontSize: 16, fontWeight: "700", color: COLORS.muted, marginLeft: 2 },
  statusDescription: {
    marginTop: 10,
    fontSize: 14,
    fontWeight: "700",
    lineHeight: 20,
  },

  noticeCard: {
    backgroundColor: COLORS.amberBg,
    borderColor: COLORS.amberBorder,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  noticeTitle: { color: COLORS.amberText, fontWeight: "800", fontSize: 13 },
  noticeText: { color: COLORS.text, marginTop: 4, fontSize: 13, lineHeight: 18 },

  sectionTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: COLORS.navy,
    marginTop: 4,
    letterSpacing: 0.3,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  dataCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingHorizontal: 16,
  },
  fieldRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  fieldLabel: {
    fontSize: 11,
    fontWeight: "800",
    color: COLORS.muted,
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  fieldValue: {
    marginTop: 4,
    fontSize: 15,
    lineHeight: 20,
    color: COLORS.text,
    fontWeight: "600",
  },
  missingValue: { color: "#94A3B8", fontStyle: "italic", fontWeight: "400" },

  compliantNotice: {
    backgroundColor: COLORS.greenBg,
    borderColor: COLORS.greenBorder,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  compliantNoticeIcon: { fontSize: 22 },
  compliantNoticeText: {
    color: COLORS.greenText,
    fontWeight: "700",
    fontSize: 14,
    flex: 1,
    lineHeight: 20,
  },

  violationCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 16,
    gap: 8,
  },
  violationCritical: { borderLeftWidth: 4, borderLeftColor: COLORS.redText },
  violationMajor: { borderLeftWidth: 4, borderLeftColor: COLORS.orangeText },
  violationMinor: { borderLeftWidth: 4, borderLeftColor: COLORS.amberText },
  violationHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  severityTag: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  tagCritical: { backgroundColor: COLORS.redBg },
  tagMajor: { backgroundColor: COLORS.orangeBg },
  tagMinor: { backgroundColor: COLORS.amberBg },
  severityTagText: { fontSize: 11, fontWeight: "800", letterSpacing: 0.4 },
  penaltyBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  penaltyCritical: { backgroundColor: COLORS.redBg },
  penaltyMajor: { backgroundColor: COLORS.orangeBg },
  penaltyMinor: { backgroundColor: COLORS.amberBg },
  penaltyText: { fontSize: 12, fontWeight: "800", color: COLORS.text },
  violationRuleName: { fontSize: 15, fontWeight: "800", color: COLORS.navy },
  violationMessage: { fontSize: 14, fontWeight: "500", color: COLORS.text, lineHeight: 20 },
  citationContainer: { flexDirection: "row", gap: 4, flexWrap: "wrap", marginTop: 2 },
  citationLabel: { fontSize: 11, fontWeight: "700", color: COLORS.muted },
  citationText: { fontSize: 11, color: COLORS.muted, flex: 1 },

  actionButton: {
    backgroundColor: COLORS.navy,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 8,
    elevation: 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  actionButtonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "800" },
  pressed: { opacity: 0.85 },
});
