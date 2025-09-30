'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink, Clock, Search, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus } from '@/lib/types';

interface SimilarTicket {
  id: string;
  title: string;
  description: string;
  team_name: string;
  status: TicketStatus;
  similarity_score: number;
  created_at: string;
}

interface SimilaritySuggestionsProps {
  title: string;
  description: string;
  className?: string;
}

export function SimilaritySuggestions({ title, description, className }: SimilaritySuggestionsProps) {
  const [debouncedText, setDebouncedText] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      const combinedText = `${title} ${description}`.trim();
      if (combinedText.length > 1) {
        setDebouncedText(combinedText);
      } else {
        setDebouncedText('');
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [title, description]);

  const { data: similarTickets, isLoading, error } = useQuery({
    queryKey: ['similar-tickets', debouncedText],
    queryFn: () => apiClient.findSimilarTickets(debouncedText, 5),
    enabled: debouncedText.length > 0,
    staleTime: 30000,
  });

  const formatStatus = (status: TicketStatus) => {
    return status.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const getStatusColor = (status: TicketStatus) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'in_review':
        return 'bg-purple-100 text-purple-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'closed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600';
    if (score >= 0.6) return 'text-orange-600'; 
    return 'text-blue-600'; 
  };

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.8) return 'Very Similar';
    if (score >= 0.6) return 'Similar';
    return 'Related';
  };

  if (debouncedText.length === 0) {
    return (
      <div className={`bg-purple-50 p-6 rounded-lg shadow-md ${className}`}>
        <h4 className="flex items-center gap-2 mb-3">
          <Search className="w-4 h-4 text-purple-600" />
          Similar Tickets
        </h4>
        <p className="text-sm text-muted-foreground">
          Start typing a title and description to see similar tickets...
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`bg-purple-50 p-6 rounded-lg shadow-md ${className}`}>
        <h4 className="flex items-center gap-2 mb-3">
          <Search className="w-4 h-4 text-purple-600" />
          Finding Similar Tickets...
        </h4>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-3/4" />
              <div className="flex space-x-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-20" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-red-50 p-6 rounded-lg shadow-md ${className}`}>
        <h4 className="flex items-center gap-2 mb-3">
          <AlertCircle className="w-4 h-4 text-red-600" />
          Error Loading Similar Tickets
        </h4>
        <p className="text-sm text-muted-foreground">
          Unable to load similar tickets. Please try again later.
        </p>
      </div>
    );
  }

  if (!similarTickets || similarTickets.length === 0) {
    return (
      <div className={`bg-green-50 p-6 rounded-lg shadow-md ${className}`}>
        <h4 className="flex items-center gap-2 mb-3">
          <Search className="w-4 h-4 text-green-600" />
          No Similar Tickets Found
        </h4>
        <p className="text-sm text-muted-foreground">
          Great! This appears to be a unique issue. No similar tickets were found.
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-purple-50 p-6 rounded-lg shadow-md space-y-4 ${className}`}>
      <h4 className="flex items-center gap-2">
        <Search className="w-4 h-4 text-purple-600" />
        Similar Tickets Found ({similarTickets.length})
      </h4>

      <div className="text-sm text-muted-foreground">
        Review these similar tickets before creating a new one to avoid duplicates:
      </div>

      {similarTickets.map((ticket) => (
        <div
          key={ticket.id}
          className="bg-white border border-purple-200 rounded-lg p-3 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {ticket.title}
              </h4>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {ticket.description}
              </p>
            </div>
            <div className="ml-3 flex-shrink-0">
              <span className={`text-xs font-medium ${getSimilarityColor(ticket.similarity_score)}`}>
                {getSimilarityLabel(ticket.similarity_score)}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className={`${getStatusColor(ticket.status as TicketStatus)} text-xs`}>
                {formatStatus(ticket.status as TicketStatus)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {ticket.team_name}
              </span>
              <span className="text-xs text-muted-foreground flex items-center">
                <Clock className="w-3 h-3 mr-1" />
                {new Date(ticket.created_at).toLocaleDateString()}
              </span>
            </div>

            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-6 px-2"
              onClick={() => window.open(`/tickets/${ticket.id}`, '_blank')}
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              View
            </Button>
          </div>

          {ticket.similarity_score >= 0.8 && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              <AlertCircle className="w-3 h-3 inline mr-1" />
              <strong>Potential Duplicate:</strong> This ticket seems very similar to yours.
              Consider commenting on the existing ticket instead.
            </div>
          )}
        </div>
      ))}

      <div className="text-xs text-muted-foreground pt-2 border-t border-purple-200">
        💡 Tip: If your issue is similar but different, mention the related ticket number in your description.
      </div>
    </div>
  );
}