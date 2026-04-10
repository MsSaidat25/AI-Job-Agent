/** Application/Kanban state management */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getBoard, moveCard } from "../api/endpoints/kanban";
import type { KanbanBoardResponse, MoveCardRequest, MoveCardResponse } from "../types/api";

interface ApplicationState {
  board: KanbanBoardResponse | null;
  isLoading: boolean;
  error: string | null;
  loadBoard: () => Promise<void>;
  moveCard: (cardId: string, req: MoveCardRequest) => Promise<MoveCardResponse>;
}

export const useApplicationStore = create<ApplicationState>()(
  persist(
    (set) => ({
      board: null,
      isLoading: false,
      error: null,

      loadBoard: async () => {
        set({ isLoading: true, error: null });
        try {
          const board = await getBoard();
          set({ board, isLoading: false });
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to load board";
          set({ isLoading: false, error: message });
        }
      },

      moveCard: async (cardId: string, req: MoveCardRequest) => {
        const response = await moveCard(cardId, req);
        // Optimistically move the card in local state
        set((state) => {
          if (!state.board) return state;
          const columns = state.board.columns.map((col) => ({
            ...col,
            cards: col.cards.filter((c) => c.id !== cardId),
          }));
          const card = state.board.columns
            .flatMap((c) => c.cards)
            .find((c) => c.id === cardId);
          if (card) {
            const targetCol = columns.find((c) => c.status === req.new_status);
            if (targetCol) {
              targetCol.cards.push({ ...card, status: req.new_status });
            }
          }
          return { board: { ...state.board, columns } };
        });
        return response;
      },
    }),
    {
      name: "application-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ board: state.board }),
    }
  )
);
