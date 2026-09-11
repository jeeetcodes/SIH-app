import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

const COLORS = {
  navy: "#1B365D",
  offWhite: "#F6F4EF",
  card: "#FFFFFF",
  text: "#1A2433",
  muted: "#5C6773",
  border: "#D9D4C8",
};

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile</Text>
      </View>
      <View style={styles.content}>
        <View style={styles.card}>
          <Text style={styles.icon}>👤</Text>
          <Text style={styles.title}>Profile</Text>
          <Text style={styles.body}>User details and settings. (Coming soon)</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.offWhite },
  header: { backgroundColor: COLORS.navy, paddingHorizontal: 20, paddingVertical: 16 },
  headerTitle: { fontSize: 22, fontWeight: "800", color: "#FFFFFF" },
  content: { flex: 1, padding: 20, justifyContent: "center" },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 32,
    alignItems: "center",
  },
  icon: { fontSize: 48, marginBottom: 16 },
  title: { fontSize: 20, fontWeight: "700", color: COLORS.navy, marginBottom: 8 },
  body: { fontSize: 14, color: COLORS.muted, textAlign: "center", lineHeight: 20 },
});
