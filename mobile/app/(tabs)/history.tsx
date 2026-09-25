import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { fetchScanHistory, type ScanHistoryItem } from "@/services/scan-api";

const COLORS = {
  navy: "#1B365D", offWhite: "#F6F4EF", card: "#FFFFFF", text: "#1A2433",
  muted: "#5C6773", border: "#D9D4C8", greenBg: "#DCFCE7", greenText: "#15803D",
  redBg: "#FEE2E2", redText: "#B91C1C",
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function ScanCard({ scan }: { scan: ScanHistoryItem }) {
  return (
    <View style={styles.scanCard}>
      <View style={styles.cardTopRow}>
        <View style={styles.productSection}>
          <Text numberOfLines={1} style={styles.productName}>{scan.product_name || "Product name not detected"}</Text>
          <Text style={styles.date}>{formatDate(scan.created_at)}</Text>
        </View>
        <Text style={styles.score}>{scan.score}/100</Text>
      </View>
      <View style={[styles.statusBadge, scan.is_compliant ? styles.compliant : styles.nonCompliant]}>
        <Text style={[styles.statusText, scan.is_compliant ? styles.compliantText : styles.nonCompliantText]}>
          {scan.is_compliant ? "✅ Compliant" : "❌ Non-Compliant"}
        </Text>
      </View>
    </View>
  );
}

export default function HistoryScreen() {
  const insets = useSafeAreaInsets();
  const [scans, setScans] = useState<ScanHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setScans(await fetchScanHistory());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Your scan history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadHistory(); }, [loadHistory]);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Scans</Text>
        <Text style={styles.headerSubtitle}>Your recent label inspections</Text>
      </View>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {loading ? (
          <View style={styles.stateCard}><ActivityIndicator color={COLORS.navy} /><Text style={styles.stateText}>Loading your scans…</Text></View>
        ) : error ? (
          <View style={styles.stateCard}>
            <Text style={styles.stateTitle}>Could not load scans</Text><Text style={styles.stateText}>{error}</Text>
            <Pressable onPress={loadHistory} style={styles.retryButton}><Text style={styles.retryText}>Try again</Text></Pressable>
          </View>
        ) : scans.length === 0 ? (
          <View style={styles.stateCard}>
            <Text style={styles.emptyIcon}>📋</Text><Text style={styles.stateTitle}>No scans yet</Text>
            <Text style={styles.stateText}>Completed label inspections will appear here.</Text>
          </View>
        ) : scans.map((scan) => <ScanCard key={scan.id} scan={scan} />)}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.offWhite },
  header: { backgroundColor: COLORS.navy, paddingHorizontal: 20, paddingVertical: 16 },
  headerTitle: { fontSize: 22, fontWeight: "800", color: "#FFFFFF" },
  headerSubtitle: { fontSize: 13, color: "#CBD5E1", marginTop: 2 },
  content: { padding: 20, gap: 12, paddingBottom: 40, flexGrow: 1 },
  stateCard: { flex: 1, minHeight: 220, justifyContent: "center", alignItems: "center", backgroundColor: COLORS.card, borderRadius: 16, borderWidth: 1, borderColor: COLORS.border, padding: 28 },
  stateTitle: { color: COLORS.navy, fontSize: 18, fontWeight: "700", marginBottom: 8, textAlign: "center" },
  stateText: { color: COLORS.muted, fontSize: 14, lineHeight: 20, textAlign: "center", marginTop: 12 },
  emptyIcon: { fontSize: 42, marginBottom: 12 },
  retryButton: { backgroundColor: COLORS.navy, borderRadius: 8, paddingHorizontal: 18, paddingVertical: 10, marginTop: 18 },
  retryText: { color: "#FFFFFF", fontWeight: "700" },
  scanCard: { backgroundColor: COLORS.card, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, padding: 16 },
  cardTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: 12 },
  productSection: { flex: 1 },
  productName: { color: COLORS.text, fontSize: 16, fontWeight: "700" },
  date: { color: COLORS.muted, fontSize: 13, marginTop: 5 },
  score: { color: COLORS.navy, fontSize: 19, fontWeight: "800" },
  statusBadge: { alignSelf: "flex-start", borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, marginTop: 14 },
  statusText: { fontSize: 12, fontWeight: "800" },
  compliant: { backgroundColor: COLORS.greenBg }, nonCompliant: { backgroundColor: COLORS.redBg },
  compliantText: { color: COLORS.greenText }, nonCompliantText: { color: COLORS.redText },
});
