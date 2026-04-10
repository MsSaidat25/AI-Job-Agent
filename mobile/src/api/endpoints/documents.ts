/** Document generation & export endpoints */

import api from "../client";
import { DOCUMENT_TIMEOUT } from "../../utils/constants";
import type {
  ResumeRequest,
  CoverLetterRequest,
  AgentResponse,
  TemplateListResponse,
  TemplateInfo,
  ExportRequest,
} from "../../types/api";

export async function generateResume(req: ResumeRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/documents/resume", req, {
    timeout: DOCUMENT_TIMEOUT,
  });
  return data;
}

export async function generateCoverLetter(req: CoverLetterRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/documents/cover-letter", req, {
    timeout: DOCUMENT_TIMEOUT,
  });
  return data;
}

export async function getTemplates(): Promise<TemplateListResponse> {
  const { data } = await api.get<TemplateListResponse>("/api/documents/templates");
  return data;
}

export async function getTemplate(templateId: string): Promise<TemplateInfo> {
  const { data } = await api.get<TemplateInfo>(`/api/documents/templates/${templateId}`);
  return data;
}

export async function exportDocument(req: ExportRequest): Promise<ArrayBuffer> {
  const { data } = await api.post("/api/documents/export", req, {
    responseType: "arraybuffer",
    timeout: DOCUMENT_TIMEOUT,
  });
  return data as ArrayBuffer;
}
