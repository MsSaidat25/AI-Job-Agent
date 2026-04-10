/** Kanban board endpoints */

import api from "../client";
import type {
  KanbanBoardResponse,
  KanbanCard,
  MoveCardRequest,
  MoveCardResponse,
} from "../../types/api";

export async function getBoard(): Promise<KanbanBoardResponse> {
  const { data } = await api.get<KanbanBoardResponse>("/api/kanban/board");
  return data;
}

export async function getCard(cardId: string): Promise<KanbanCard> {
  const { data } = await api.get<KanbanCard>(`/api/kanban/cards/${cardId}`);
  return data;
}

export async function moveCard(
  cardId: string,
  req: MoveCardRequest
): Promise<MoveCardResponse> {
  const { data } = await api.put<MoveCardResponse>(
    `/api/kanban/cards/${cardId}/move`,
    req
  );
  return data;
}
