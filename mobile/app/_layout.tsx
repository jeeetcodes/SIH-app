import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen
        name="result"
        options={{
          headerShown: true,
          title: "Inspection Result",
          headerStyle: { backgroundColor: "#1B365D" },
          headerTintColor: "#FFFFFF",
          headerTitleStyle: { fontWeight: "700" },
          presentation: "card",
        }}
      />
    </Stack>
  );
}