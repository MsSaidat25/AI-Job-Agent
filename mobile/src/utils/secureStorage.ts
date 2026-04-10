/**
 * Zustand-compatible storage adapter backed by expo-secure-store.
 * Used for sensitive data (session ID, profile PII).
 * Falls back to AsyncStorage on web where SecureStore is unavailable.
 */

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { StateStorage } from "zustand/middleware";

const isNative = Platform.OS === "ios" || Platform.OS === "android";

export const secureStorage: StateStorage = {
  getItem: async (name: string): Promise<string | null> => {
    if (isNative) {
      return SecureStore.getItemAsync(name);
    }
    return AsyncStorage.getItem(name);
  },

  setItem: async (name: string, value: string): Promise<void> => {
    if (isNative) {
      await SecureStore.setItemAsync(name, value);
      return;
    }
    await AsyncStorage.setItem(name, value);
  },

  removeItem: async (name: string): Promise<void> => {
    if (isNative) {
      await SecureStore.deleteItemAsync(name);
      return;
    }
    await AsyncStorage.removeItem(name);
  },
};
