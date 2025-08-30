import React from 'react';
import { Badge } from './badge';
import { Avatar, AvatarFallback } from './avatar';
import { Ticket } from '@/lib/types';
import { 
  getTicketCreatorInfo,
  getActorDisplayName,
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

  if (!creatorInfo.creator) {
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

  const actor = creatorInfo.creator;
  const displayName = getActorDisplayName(actor);

  if (creatorInfo.isSystemCreated && actor.system_user_type) {
    const icon = getSystemUserIcon(actor.system_user_type);
    const typeLabel = getSystemUserTypeLabel(actor.system_user_type);
    const colorClass = getSystemUserColor(actor.system_user_type);

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
    return (
      <div className="flex items-center space-x-2">
        {showAvatar && (
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-xs">
              {displayName.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        )}
        <span className="text-sm text-gray-600">{displayName}</span>
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

  if (!creatorInfo.creator) {
    return (
      <Badge variant="outline" className="text-xs text-gray-400">
        Unknown Creator
      </Badge>
    );
  }

  const actor = creatorInfo.creator;

  if (creatorInfo.isSystemCreated && actor.system_user_type) {
    const icon = getSystemUserIcon(actor.system_user_type);
    const typeLabel = getSystemUserTypeLabel(actor.system_user_type);

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