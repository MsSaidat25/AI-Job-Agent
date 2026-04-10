/** Chat endpoints */

import api from "../client";
import type { ChatRequest, AgentResponse, ResumeParseResponse } from "../../types/api";
import { DOCUMENT_TIMEOUT } from "../../utils/constants";

export async function sendMessage(req: ChatRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/chat", req, {
    timeout: DOCUMENT_TIMEOUT,
  });
  return data;
}

export async function resetChat(): Promise<void> {
  await api.delete("/api/chat/reset");
}

export async function parseResume(file: {
  uri: string;
  name: string;
  type: string;
}): Promise<ResumeParseResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.type,
  } as unknown as Blob);

  const { data } = await api.post<ResumeParseResponse>("/api/parse-resume", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: DOCUMENT_TIMEOUT,
  });
  return data;
}
