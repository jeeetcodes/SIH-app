import { useMemo, type FC } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import type { ScanResponse } from "@/services/scan-api";
import { InspectionResultView } from "@/components/inspection-result-view";

const COLORS = {
  navy: "#1B365D",
  offWhite: "#F8FAFC",
  muted: "#64748B",
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
  const rawImageUri = Array.isArray(params.imageUri) ? params.imageUri[0] : params.imageUri;
  const imageUri = useMemo(() => {
    if (!rawImageUri) return null;
    try {
      return decodeURIComponent(rawImageUri);
    } catch {
      return rawImageUri;
    }
  }, [rawImageUri]);

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
      <InspectionResultView
        imageUri={imageUri}
        report={report}
        onScanAgain={() => router.replace("/(tabs)")}
      />
    </View>
  );
};

export default Result;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.offWhite },
  centered: { flex: 1, padding: 24, justifyContent: "center", backgroundColor: COLORS.offWhite },
  title: { fontSize: 22, fontWeight: "700", color: COLORS.navy, marginBottom: 8 },
  body: { fontSize: 15, lineHeight: 22, color: COLORS.muted, marginBottom: 16 },
  button: {
    backgroundColor: COLORS.navy,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  buttonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
});
