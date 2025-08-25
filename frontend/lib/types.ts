// API Response Types
export interface User {
  id: string;
  email: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  members_count?: number;
}

export interface TeamMember {
  team_id: string;
  user_id: string;
  role: 'manager' | 'member';
  joined_at?: string;
}

export interface Ticket {
  id: string;
  team_id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  assignee_id?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  last_activity_at?: string;
  tags?: string[];
  comments_count?: number;
  team_name?: string;
}

export interface TicketCreate {
  team_id: string;
  title: string;
  description: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  assignee_id?: string;
}

export interface TicketUpdate {
  team_id?: string;
  title?: string;
  description?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  assignee_id?: string;
}

export interface TicketList {
  tickets: Ticket[];
  total: number;
  page: number;
  page_size: number;
}

export interface Comment {
  id: string;
  ticket_id: string;
  content: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface Tag {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
}

export type TicketStatus = 
  | 'open' 
  | 'in_progress' 
  | 'in_review' 
  | 'resolved' 
  | 'closed' 
  | 'blocked' 
  | 'on_hold';

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export type TeamRole = 'manager' | 'member';

// Filter types
export interface TicketFilters {
  team_id?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  assignee_id?: string;
  created_by?: string;
  tags?: string[];
  commented_by?: string;
  q?: string;
  page?: number;
  page_size?: number;
}