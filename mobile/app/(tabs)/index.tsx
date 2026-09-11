import { useCallback, useState, type FC } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { type Href, useRouter } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { analyzeLabelImage, ScanApiError } from "@/services/scan-api";

const COLORS = {
  navy: "#1B365D",
  navyMuted: "#2C4A6E",
  offWhite: "#F6F4EF",
  card: "#FFFFFF",
  text: "#1A2433",
  muted: "#5C6773",
  border: "#D9D4C8",
  white: "#FFFFFF",
  accent: "#2563EB",
  accentLight: "#EFF6FF",
} as const;

const pickerOptions: ImagePicker.ImagePickerOptions = {
  mediaTypes: ["images"],
  quality: 0.9,
  // Preserve the complete label rather than asking the user to crop it.
  allowsEditing: false,
};

const ScanHome: FC = () => {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [image, setImage] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const applyPickerResult = useCallback((result: ImagePicker.ImagePickerResult) => {
    if (result.canceled) {
      return;
    }
    const asset = result.assets[0];
    if (asset?.uri) {
      setImage(asset);
    }
  }, []);

  const handleScanLabel = useCallback(async () => {
    const existing = await ImagePicker.getCameraPermissionsAsync();
    const permission = existing.granted
      ? existing
      : await ImagePicker.requestCameraPermissionsAsync();

    if (!permission.granted) {
      Alert.alert(
        "Camera permission required",
        "Allow camera access in Settings to photograph a package label for inspection."
      );
      return;
    }

    const result = await ImagePicker.launchCameraAsync(pickerOptions);
    applyPickerResult(result);
  }, [applyPickerResult]);

  const handleChooseFromGallery = useCallback(async () => {
    const existing = await ImagePicker.getMediaLibraryPermissionsAsync();
    const permission = existing.granted
      ? existing
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert(
        "Photo library permission required",
        "Allow photo access in Settings to select an existing package label image."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync(pickerOptions);
    applyPickerResult(result);
  }, [applyPickerResult]);

  const handleAnalyzeLabel = useCallback(async () => {
    if (!image || isAnalyzing) {
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await analyzeLabelImage(image);
      router.push({
        pathname: "/result",
        params: { imageUri: image.uri, report: JSON.stringify(result) },
      } as unknown as Href);
    } catch (error) {
      if (error instanceof ScanApiError && error.status === 503) {
        Alert.alert("Server is busy", "Server is busy. Please try again.");
      } else if (error instanceof ScanApiError && error.status === 400) {
        Alert.alert(
          "Valid product label not detected",
          "Valid product label not detected. Please upload a valid label photo."
        );
      } else {
        const message =
          error instanceof ScanApiError
            ? error.message
            : "Label unreadable or server unavailable. Please retake the photo with better lighting.";
        Alert.alert("Analysis Error", message);
      }
    } finally {
      setIsAnalyzing(false);
    }
  }, [image, isAnalyzing, router]);

  const handleClearPreview = useCallback(() => {
    setImage(null);
  }, []);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Label Police</Text>
        <Text style={styles.headerSubtitle}>Legal Metrology Compliance Inspector</Text>
      </View>

      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 80 }]}
        showsVerticalScrollIndicator={false}>
        {/* Main Camera / Preview Frame */}
        {image ? (
          <View style={styles.previewCard}>
            <View style={styles.previewHeader}>
              <Text style={styles.previewTag}>READY FOR INSPECTION</Text>
              <Pressable onPress={handleClearPreview} style={styles.removeBtn}>
                <Text style={styles.removeBtnText}>Clear</Text>
              </Pressable>
            </View>

            <Image
              source={{ uri: image.uri }}
              style={styles.previewImage}
              resizeMode="contain"
              accessibilityLabel="Captured packaging label preview"
            />
          </View>
        ) : (
          <View style={styles.cameraBox}>
            {/* Viewfinder frame overlay */}
            <View style={styles.viewfinderGuide}>
              <View style={[styles.corner, styles.topLeft]} />
              <View style={[styles.corner, styles.topRight]} />
              <View style={[styles.corner, styles.bottomLeft]} />
              <View style={[styles.corner, styles.bottomRight]} />

              <Text style={styles.guideIcon}>🔍</Text>
              <Text style={styles.guideTitle}>Align Product Label Here</Text>
              <Text style={styles.guideSubtitle}>
                Ensure MRP, Net Qty, Dates & Consumer Care details are clearly visible
              </Text>
            </View>
          </View>
        )}

        {/* Action Controls */}
        <View style={styles.controlsGroup}>
          {image ? (
            <Pressable
              onPress={handleAnalyzeLabel}
              disabled={isAnalyzing}
              style={({ pressed }) => [styles.analyzeBtn, pressed && styles.pressed]}>
              <Text style={styles.analyzeBtnText}>⚡ Audit Label Compliance</Text>
            </Pressable>
          ) : (
            <Pressable
              onPress={handleScanLabel}
              style={({ pressed }) => [styles.shutterBtn, pressed && styles.pressed]}>
              <View style={styles.shutterInner}>
                <Text style={styles.shutterIcon}>📸</Text>
              </View>
              <Text style={styles.shutterText}>Snap Label Photo</Text>
            </Pressable>
          )}

          <Pressable
            onPress={handleChooseFromGallery}
            style={({ pressed }) => [styles.galleryBtn, pressed && styles.pressed]}>
            <Text style={styles.galleryBtnText}>
              {image ? "Choose Different Image" : "📁 Choose from Gallery"}
            </Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* Futuristic Analyzing Loading Modal Overlay */}
      <Modal visible={isAnalyzing} transparent animationType="fade">
        <View style={styles.loadingOverlay}>
          <View style={styles.loadingCard}>
            <ActivityIndicator size="large" color={COLORS.navy} />
            <Text style={styles.loadingTitle}>Analyzing Label...</Text>
            <Text style={styles.loadingBody}>
              Performing high-precision visual audit against Legal Metrology Rules 2011
            </Text>
          </View>
        </View>
      </Modal>
    </View>
  );
};

export default ScanHome;

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: COLORS.offWhite,
  },
  header: {
    backgroundColor: COLORS.navy,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: COLORS.white,
    letterSpacing: 0.5,
  },
  headerSubtitle: {
    fontSize: 13,
    color: "#A0AEC0",
    marginTop: 2,
  },
  content: {
    padding: 20,
    gap: 18,
  },
  cameraBox: {
    height: 380,
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: COLORS.border,
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  viewfinderGuide: {
    width: "100%",
    height: "100%",
    borderWidth: 1.5,
    borderColor: "#CBD5E1",
    borderStyle: "dashed",
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
    position: "relative",
  },
  corner: {
    position: "absolute",
    width: 24,
    height: 24,
    borderColor: COLORS.navy,
  },
  topLeft: { top: 8, left: 8, borderTopWidth: 3, borderLeftWidth: 3 },
  topRight: { top: 8, right: 8, borderTopWidth: 3, borderRightWidth: 3 },
  bottomLeft: { bottom: 8, left: 8, borderBottomWidth: 3, borderLeftWidth: 3 },
  bottomRight: { bottom: 8, right: 8, borderBottomWidth: 3, borderRightWidth: 3 },
  guideIcon: { fontSize: 36, marginBottom: 12 },
  guideTitle: { fontSize: 18, fontWeight: "700", color: COLORS.navy, marginBottom: 6 },
  guideSubtitle: { fontSize: 13, color: COLORS.muted, textAlign: "center", lineHeight: 18 },

  previewCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 12,
    gap: 10,
  },
  previewHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 4,
  },
  previewTag: { fontSize: 11, fontWeight: "800", color: COLORS.navy, letterSpacing: 0.8 },
  removeBtn: { paddingVertical: 4, paddingHorizontal: 8 },
  removeBtnText: { fontSize: 13, fontWeight: "600", color: "#E53E3E" },
  previewImage: {
    width: "100%",
    height: 400,
    maxHeight: 400,
    borderRadius: 12,
    backgroundColor: COLORS.offWhite,
  },

  controlsGroup: {
    gap: 12,
  },
  shutterBtn: {
    backgroundColor: COLORS.navy,
    paddingVertical: 16,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    elevation: 3,
  },
  shutterInner: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  shutterIcon: { fontSize: 14 },
  shutterText: { color: COLORS.white, fontSize: 17, fontWeight: "700" },

  analyzeBtn: {
    backgroundColor: "#166534",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  analyzeBtnText: { color: COLORS.white, fontSize: 17, fontWeight: "800" },

  galleryBtn: {
    backgroundColor: COLORS.card,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  galleryBtnText: { color: COLORS.navy, fontSize: 15, fontWeight: "600" },

  pressed: { opacity: 0.85 },

  loadingOverlay: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.7)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  loadingCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 28,
    alignItems: "center",
    width: "90%",
    elevation: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 10,
  },
  loadingTitle: { fontSize: 19, fontWeight: "700", color: COLORS.navy, marginTop: 16, marginBottom: 8 },
  loadingBody: { fontSize: 14, color: COLORS.muted, textAlign: "center", lineHeight: 20 },
});
