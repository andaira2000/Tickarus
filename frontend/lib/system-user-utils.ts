import { Ticket, SystemUserType, ActorInfo } from './types';

export function getTicketCreatorInfo(ticket: Ticket) {
  const creatorInfo = ticket.creator_info;
  
  if (!creatorInfo) {
    return {
      isSystemCreated: false,
      isUserCreated: false,
      creator: null
    };
  }
  
  const isSystemCreated = creatorInfo.actor_type === 'system';
  const isUserCreated = creatorInfo.actor_type === 'human';
  
  return {
    isSystemCreated,
    isUserCreated,
    creator: creatorInfo
  };
}

export function getActorDisplayName(actor: ActorInfo): string {
  return actor.display_name;
}

export function getSystemUserIcon(systemUserType: SystemUserType): string {
  switch (systemUserType) {
    case 'ci_automation':
      return '🔧';
    case 'ai_assistant':
      return '🤖';
    case 'data_processor':
      return '📊';
    case 'notification_service':
      return '📢';
    default:
      return '⚙️';
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