export interface User {
  id: string;
  email: string;
  full_name?: string;
}

export interface SystemUser {
  id: string;
  name: string;
  type: SystemUserType;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export type SystemUserType = 
  | 'ci_automation' 
  | 'ai_assistant' 
  | 'data_processor' 
  | 'notification_service';

export type ActorType = 'human' | 'system';

export interface ActorInfo {
  id: string;
  actor_type: ActorType;
  display_name: string;
  avatar_url?: string;
  is_system: boolean;
  system_user_type?: SystemUserType;
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
  actor_id: string;
  created_at: string;
  updated_at?: string;
  last_activity_at?: string;
  tags?: string[];
  comment_count?: number;
  team_name?: string;
  creator_info?: ActorInfo;
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
  actor_id: string;
  created_at: string;
  updated_at?: string;
  author_info?: ActorInfo;
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

export interface TicketFilters {
  team_id?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  assignee_id?: string;
  tag_names?: string[];
  commented_by?: string;
  search_query?: string;
  page?: number;
  page_size?: number;
  created_by_me?: boolean;
}

export interface ChatSession {
  id: string;
  ticket_id: string;
  user_id: string;
  title?: string;
  status: 'active' | 'closed';
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, unknown>;
  token_count?: number;
  created_at: string;
}

export interface ChatSessionCreate {
  ticket_id: string;
  title?: string;
  initial_message?: string;
}

export interface ChatMessageCreate {
  content: string;
  role: 'user';
}

export interface ChatResponse {
  message: ChatMessage;
  session_updated: boolean;
  context_used?: Record<string, unknown>;
}