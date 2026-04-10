/** Typed AsyncStorage helpers */

import AsyncStorage from "@react-native-async-storage/async-storage";

export async function getItem<T>(key: string): Promise<T | null> {
  const raw = await AsyncStorage.getItem(key);
  if (raw === null) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    // Raw value is not valid JSON -- return null instead of unsafe cast
    return null;
  }
}

export async function setItem<T>(key: string, value: T): Promise<void> {
  const raw = typeof value === "string" ? value : JSON.stringify(value);
  await AsyncStorage.setItem(key, raw);
}

export async function removeItem(key: string): Promise<void> {
  await AsyncStorage.removeItem(key);
}
