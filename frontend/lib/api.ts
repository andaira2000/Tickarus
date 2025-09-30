import axios from 'axios';
import {
  AuthResponse,
  User,
  SystemUser,
  Team,
  TeamMember,
  Ticket,
  TicketCreate,
  TicketUpdate,
  TicketList,
  Comment,
  Tag,
  TicketFilters,
  TeamRole,
  ChatSession,
  ChatSessionCreate,
  ChatMessage,
  ChatMessageCreate,
  ChatResponse
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_USE_CLOUD_API === 'false' ? process.env.NEXT_PUBLIC_LOCALHOST_URL : process.env.NEXT_PUBLIC_API_URL;

class ApiClient {
  private client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  constructor() {
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async register(email: string, password: string, full_name?: string) {
    const response = await this.client.post<{ user_id: string; email: string }>('/api/auth/register', {
      email,
      password,
      full_name,
    });
    return response.data;
  }

  async login(email: string, password: string) {
    const response = await this.client.post<AuthResponse>('/api/auth/login', {
      email,
      password,
    });
    

    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get<User>('/api/auth/me');
    return response.data;
  }

  async getTeams() {
    const response = await this.client.get<Team[]>('/api/teams');
    return response.data;
  }

  async createTeam(name: string, description?: string) {
    const response = await this.client.post<Team>('/api/teams', {
      name,
      description,
    });
    return response.data;
  }

  async updateTeam(teamId: string, data: { name?: string; description?: string }) {
    const response = await this.client.patch<Team>(`/api/teams/${teamId}`, data);
    return response.data;
  }

  async getTeamMembers(teamId: string) {
    const response = await this.client.get<TeamMember[]>(`/api/teams/${teamId}/members`);
    return response.data;
  }

  async addTeamMember(teamId: string, userId: string, role: TeamRole = 'member') {
    const response = await this.client.post<TeamMember>(`/api/teams/${teamId}/members/${userId}?role=${role}`);
    return response.data;
  }

  async updateTeamMember(teamId: string, userId: string, role: TeamRole) {
    const response = await this.client.patch<TeamMember>(`/api/teams/${teamId}/members/${userId}`, { role });
    return response.data;
  }

  async removeTeamMember(teamId: string, userId: string) {
    await this.client.delete(`/api/teams/${teamId}/members/${userId}`);
  }

  async getTickets(filters: TicketFilters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(v => params.append(key, v));
        } else {
          params.set(key, value.toString());
        }
      }
    });

    const response = await this.client.get<TicketList>(`/api/tickets?${params.toString()}`);
    return response.data;
  }

  async getTicket(ticketId: string) {
    const response = await this.client.get<Ticket>(`/api/tickets/${ticketId}`);
    return response.data;
  }

  async createTicket(ticket: TicketCreate) {
    const response = await this.client.post<Ticket>('/api/tickets', ticket);
    return response.data;
  }

  async updateTicket(ticketId: string, updates: TicketUpdate) {
    const response = await this.client.patch<Ticket>(`/api/tickets/${ticketId}`, updates);
    return response.data;
  }

  async addTicketTags(ticketId: string, tags: string[]) {
    await this.client.post(`/api/tickets/${ticketId}/tags`, tags);
  }

  async removeTicketTags(ticketId: string, tags: string[]) {
    await this.client.delete(`/api/tickets/${ticketId}/tags`, { data: tags });
  }

  async watchTicket(ticketId: string) {
    await this.client.post(`/api/tickets/${ticketId}/watch`);
  }

  async unwatchTicket(ticketId: string) {
    await this.client.delete(`/api/tickets/${ticketId}/watch`);
  }

  async getComments(ticketId: string) {
    const response = await this.client.get<Comment[]>(`/api/comments/ticket/${ticketId}`);
    return response.data;
  }

  async createComment(ticketId: string, content: string) {
    const response = await this.client.post<Comment>('/api/comments', {
      ticket_id: ticketId,
      content,
    });
    return response.data;
  }

  async updateComment(commentId: string, content: string) {
    const response = await this.client.patch<Comment>(`/api/comments/${commentId}`, {
      content,
    });
    return response.data;
  }

  async deleteComment(commentId: string) {
    await this.client.delete(`/api/comments/${commentId}`);
  }

  async getTags() {
    const response = await this.client.get<Tag[]>('/api/tags');
    return response.data;
  }

  async createTag(name: string) {
    const response = await this.client.post<Tag>('/api/tags', { name });
    return response.data;
  }

  async getPopularTags(limit = 10) {
    const response = await this.client.get<{ name: string; count: number }[]>(`/api/tags/popular?limit=${limit}`);
    return response.data;
  }

  async getSystemUsers() {
    const response = await this.client.get<SystemUser[]>('/api/system-users');
    return response.data;
  }

  async getSystemUser(systemUserId: string) {
    const response = await this.client.get<SystemUser>(`/api/system-users/${systemUserId}`);
    return response.data;
  }

  async createChatSession(sessionData: ChatSessionCreate) {
    const response = await this.client.post<ChatSession>('/api/ai-chat/sessions', sessionData);
    return response.data;
  }

  async getChatSessions(limit = 20) {
    const response = await this.client.get<ChatSession[]>(`/api/ai-chat/sessions?limit=${limit}`);
    return response.data;
  }

  async getChatSession(sessionId: string) {
    const response = await this.client.get<{ messages: ChatMessage[] } & ChatSession>(`/api/ai-chat/sessions/${sessionId}`);
    return response.data;
  }

  async sendChatMessage(sessionId: string, messageData: ChatMessageCreate) {
    const response = await this.client.post<ChatResponse>(`/api/ai-chat/sessions/${sessionId}/messages`, messageData);
    return response.data;
  }

  async getChatMessages(sessionId: string, limit = 50) {
    const response = await this.client.get<ChatMessage[]>(`/api/ai-chat/sessions/${sessionId}/messages?limit=${limit}`);
    return response.data;
  }

  async closeChatSession(sessionId: string) {
    await this.client.post(`/api/ai-chat/sessions/${sessionId}/close`);
  }

  async getTicketChatSessions(ticketId: string) {
    const response = await this.client.get<ChatSession[]>(`/api/ai-chat/tickets/${ticketId}/sessions`);
    return response.data;
  }

  async findSimilarTickets(ticketText: string, limit = 5) {
    const response = await this.client.post<Array<{
      id: string;
      title: string;
      description: string;
      team_name: string;
      status: string;
      similarity_score: number;
      created_at: string;
    }>>('/api/tickets/similar', {
      ticket_text: ticketText,
      limit
    });
    return response.data;
  }

  async getAIRootCauseAnalysis(ticketId: string) {
    const response = await this.client.post<{
      root_cause: string;
      confidence_score: number;
      suggestions: string[];
      similar_resolved_tickets: Array<{
        id: string;
        title: string;
        resolution: string;
      }>;
      analysis_method: string;
      llm_used: boolean;
    }>(`/api/tickets/${ticketId}/ai-analysis`);
    return response.data;
  }

  async getAutoTaggingSuggestions(title: string, description: string) {
    const response = await this.client.post<{
      suggested_tags: string[];
      suggested_priority: string;
      confidence_scores: Record<string, number>;
    }>('/api/tickets/auto-tag', {
      title,
      description
    });
    return response.data;
  }

  async logSimilarityClick(clickedTicketId: string, originalTicketId?: string) {
    await this.client.post('/api/tickets/similarity-click', {
      clicked_ticket_id: clickedTicketId,
      original_ticket_id: originalTicketId
    });
  }

  async rateAIAnalysis(ticketId: string, rating: 'helpful' | 'not_helpful') {
    await this.client.post(`/api/tickets/${ticketId}/ai-analysis/rate`, {
      rating
    });
  }
}

export const apiClient = new ApiClient();