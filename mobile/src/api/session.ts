/** Session creation -- persistence handled by Zustand store only */

import api from "./client";
import type { SessionResponse } from "../types/api";

export async function createNewSession(): Promise<string> {
  const { data } = await api.post<SessionResponse>("/api/session");
  return data.session_id;
}
