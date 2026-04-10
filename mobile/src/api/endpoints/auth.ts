/** Auth & profile endpoints */

import api from "../client";
import type { ProfileRequest, ProfileResponse } from "../../types/api";

export async function postProfile(profile: ProfileRequest): Promise<ProfileResponse> {
  const { data } = await api.post<ProfileResponse>("/api/profile", profile);
  return data;
}

export async function getProfile(): Promise<ProfileRequest> {
  const { data } = await api.get<ProfileRequest>("/api/profile");
  return data;
}
