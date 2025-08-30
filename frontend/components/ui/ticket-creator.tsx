import React from 'react';
import { Badge } from './badge';
import { Avatar, AvatarFallback } from './avatar';
import { Ticket } from '@/lib/types';
import { 
  getTicketCreatorInfo, 
  getSystemUserDisplayName, 
  getSystemUserIcon, 
  getSystemUserTypeLabel,
  getSystemUserColor 
} from '@/lib/system-user-utils';

interface TicketCreatorProps {
  ticket: Ticket;
  showAvatar?: boolean;
  showTypeLabel?: boolean;
}

export function TicketCreator({ ticket, showAvatar = true, showTypeLabel = false }: TicketCreatorProps) {
  const creatorInfo = getTicketCreatorInfo(ticket);

  if (creatorInfo.isSystemCreated && ticket.created_by_system_user) {
    const systemUser = ticket.created_by_system_user;
    const displayName = getSystemUserDisplayName(systemUser);
    const icon = getSystemUserIcon(systemUser.type);
    const typeLabel = getSystemUserTypeLabel(systemUser.type);
    const colorClass = getSystemUserColor(systemUser.type);

    return (
      <div className="flex items-center space-x-2">
        {showAvatar && (
          <Avatar className="h-6 w-6">
            <AvatarFallback className={`text-xs ${colorClass} bg-gray-100`}>
              {icon}
            </AvatarFallback>
          </Avatar>
        )}
        <div className="flex flex-col">
          <span className={`text-sm font-medium ${colorClass}`}>
            {displayName}
          </span>
          {showTypeLabel && (
            <Badge variant="outline" className="text-xs">
              {typeLabel}
            </Badge>
          )}
        </div>
      </div>
    );
  }

  if (creatorInfo.isUserCreated) {
    // For now, we'll just show the user ID since we don't have user lookup
    // In a real implementation, you'd fetch user details
    return (
      <div className="flex items-center space-x-2">
        {showAvatar && (
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-xs">
              U
            </AvatarFallback>
          </Avatar>
        )}
        <span className="text-sm text-gray-600">User</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      {showAvatar && (
        <Avatar className="h-6 w-6">
          <AvatarFallback className="text-xs">
            ?
          </AvatarFallback>
        </Avatar>
      )}
      <span className="text-sm text-gray-400">Unknown</span>
    </div>
  );
}

export function TicketCreatorBadge({ ticket }: { ticket: Ticket }) {
  const creatorInfo = getTicketCreatorInfo(ticket);

  if (creatorInfo.isSystemCreated && ticket.created_by_system_user) {
    const systemUser = ticket.created_by_system_user;
    const icon = getSystemUserIcon(systemUser.type);
    const typeLabel = getSystemUserTypeLabel(systemUser.type);

    return (
      <Badge variant="secondary" className="text-xs">
        {icon} {typeLabel}
      </Badge>
    );
  }

  if (creatorInfo.isUserCreated) {
    return (
      <Badge variant="outline" className="text-xs">
        👤 User Created
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs text-gray-400">
      Unknown Creator
    </Badge>
  );
}