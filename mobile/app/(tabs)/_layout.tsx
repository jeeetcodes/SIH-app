import { Tabs } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

const COLORS = {
  navy: "#1B365D",
  navyMuted: "#2C4A6E",
  white: "#FFFFFF",
  muted: "#8E9AA8",
  activeText: "#1B365D",
  border: "#E2E8F0",
};

function TabIcon({ icon, label, focused }: { icon: string; label: string; focused: boolean }) {
  return (
    <View style={styles.tabItem}>
      <Text style={[styles.tabIcon, focused && styles.tabIconFocused]}>{icon}</Text>
      <Text style={[styles.tabLabel, focused && styles.tabLabelFocused]}>{label}</Text>
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarShowLabel: false,
        tabBarStyle: styles.tabBar,
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: "Scan",
          tabBarIcon: ({ focused }) => <TabIcon icon="📷" label="Scan" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: "My Scans",
          tabBarIcon: ({ focused }) => <TabIcon icon="📋" label="My Scans" focused={focused} />,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    height: 64,
    paddingBottom: 8,
    paddingTop: 8,
    elevation: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  tabItem: {
    alignItems: "center",
    justifyContent: "center",
  },
  tabIcon: {
    fontSize: 20,
    marginBottom: 2,
    opacity: 0.6,
  },
  tabIconFocused: {
    opacity: 1,
    transform: [{ scale: 1.1 }],
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: COLORS.muted,
  },
  tabLabelFocused: {
    color: COLORS.activeText,
    fontWeight: "700",
  },
});
