import { Ticket, SystemUserType } from './types';

export function getTicketCreatorInfo(ticket: Ticket) {
  const isSystemCreated = !ticket.created_by && ticket.created_by_system_user_id;
  const isUserCreated = ticket.created_by && !ticket.created_by_system_user_id;
  
  return {
    isSystemCreated,
    isUserCreated,
    creator: isSystemCreated 
      ? ticket.created_by_system_user 
      : { id: ticket.created_by, type: 'user' as const }
  };
}

export function getSystemUserDisplayName(systemUser: { name: string; type: SystemUserType }): string {
  return systemUser.name;
}

export function getSystemUserIcon(systemUserType: SystemUserType): string {
  switch (systemUserType) {
    case 'ci_automation':
      return '🔧'; // wrench for CI
    case 'ai_assistant':
      return '🤖'; // robot for AI
    case 'data_processor':
      return '📊'; // chart for data processing
    case 'notification_service':
      return '📢'; // megaphone for notifications
    default:
      return '⚙️'; // gear for generic system
  }
}

export function getSystemUserTypeLabel(systemUserType: SystemUserType): string {
  switch (systemUserType) {
    case 'ci_automation':
      return 'CI Automation';
    case 'ai_assistant':
      return 'AI Assistant';
    case 'data_processor':
      return 'Data Processor';
    case 'notification_service':
      return 'Notification Service';
    default:
      return 'System User';
  }
}

export function getSystemUserColor(systemUserType: SystemUserType): string {
  switch (systemUserType) {
    case 'ci_automation':
      return 'text-blue-600';
    case 'ai_assistant':
      return 'text-purple-600';
    case 'data_processor':
      return 'text-green-600';
    case 'notification_service':
      return 'text-orange-600';
    default:
      return 'text-gray-600';
  }
}