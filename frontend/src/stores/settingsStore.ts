import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage } from '../api/types';

interface SettingsState {
    // Settings
    apiUrl: string;
    projectId: number;
    theme: 'dark' | 'light';

    // Chat History
    chatHistory: ChatMessage[];

    // Actions
    setApiUrl: (url: string) => void;
    setProjectId: (id: number) => void;
    toggleTheme: () => void;
    addMessage: (message: ChatMessage) => void;
    clearHistory: () => void;
}

export const useSettingsStore = create<SettingsState>()(
    persist(
        (set) => ({
            // Default values
            apiUrl: '/api/v1',
            projectId: 1,
            theme: 'dark',
            chatHistory: [],

            // Actions
            setApiUrl: (url) => set({ apiUrl: url }),

            setProjectId: (id) => set({ projectId: id }),

            toggleTheme: () => set((state) => ({
                theme: state.theme === 'dark' ? 'light' : 'dark'
            })),

            addMessage: (message) => set((state) => ({
                chatHistory: [...state.chatHistory, message].slice(-50), // Keep last 50 messages
            })),

            clearHistory: () => set({ chatHistory: [] }),
        }),
        {
            name: 'fehres-settings',
        }
    )
);
