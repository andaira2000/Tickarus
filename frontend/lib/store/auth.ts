import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '../types';
import { apiClient } from '../api';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isInitialized: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          await apiClient.login(email, password);
          
          const user = await apiClient.getCurrentUser();
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            isInitialized: true,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (email: string, password: string, fullName?: string) => {
        set({ isLoading: true });
        try {
          const response = await apiClient.register(email, password, fullName);
          
          const user: User = {
            id: response.user_id,
            email: response.email,
            full_name: fullName,
          };
          
          set({
            user,
            isAuthenticated: false,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({
          user: null,
          isAuthenticated: false,
          isInitialized: true,
        });
      },

      initializeAuth: async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
          try {
            const user = await apiClient.getCurrentUser();
            set({ 
              user, 
              isAuthenticated: true, 
              isInitialized: true 
            });
          } catch {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            set({ 
              user: null, 
              isAuthenticated: false, 
              isInitialized: true 
            });
          }
        } else {
          set({ isAuthenticated: false, isInitialized: true });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);