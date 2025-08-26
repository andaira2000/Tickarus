import axios from 'axios';
import { 
  AuthResponse, 
  User,
  Team, 
  TeamMember, 
  Ticket, 
  TicketCreate, 
  TicketUpdate, 
  TicketList, 
  Comment, 
  Tag, 
  TicketFilters,
  TeamRole
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  constructor() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor to handle auth errors
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

  // Auth endpoints
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
    
    // Store tokens
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get<User>('/api/auth/me');
    return response.data;
  }

  // Teams endpoints
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

  // Tickets endpoints
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

  // Comments endpoints
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

  // Tags endpoints
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
}

export const apiClient = new ApiClient();