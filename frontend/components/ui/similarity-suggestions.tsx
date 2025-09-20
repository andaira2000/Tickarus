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

  // Debounce the input to avoid too many API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      const combinedText = `${title} ${description}`.trim();
      if (combinedText.length > 10) { // Only search if we have meaningful content
        setDebouncedText(combinedText);
      } else {
        setDebouncedText('');
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [title, description]);

  // Query similar tickets
  const { data: similarTickets, isLoading, error } = useQuery({
    queryKey: ['similar-tickets', debouncedText],
    queryFn: () => apiClient.findSimilarTickets(debouncedText, 5),
    enabled: debouncedText.length > 0,
    staleTime: 30000, // Cache for 30 seconds
  });

  const formatStatus = (status: TicketStatus) => {
    return status.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const getStatusColor = (status: TicketStatus) => {
    switch (status) {
      case 'open':
        return 'destructive';
      case 'in_progress':
        return 'default';
      case 'in_review':
        return 'secondary';
      case 'resolved':
        return 'outline';
      case 'closed':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600'; // Very similar - potential duplicate
    if (score >= 0.6) return 'text-orange-600'; // Quite similar
    return 'text-blue-600'; // Somewhat similar
  };

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.8) return 'Very Similar';
    if (score >= 0.6) return 'Similar';
    return 'Related';
  };

  if (debouncedText.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <Search className="w-4 h-4 mr-2 text-gray-400" />
            Similar Tickets
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Start typing a title and description to see similar tickets...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <Search className="w-4 h-4 mr-2 text-blue-600" />
            Finding Similar Tickets...
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
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
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <AlertCircle className="w-4 h-4 mr-2 text-red-600" />
            Error Loading Similar Tickets
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Unable to load similar tickets. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!similarTickets || similarTickets.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <Search className="w-4 h-4 mr-2 text-green-600" />
            No Similar Tickets Found
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Great! This appears to be a unique issue. No similar tickets were found.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center text-sm font-medium">
          <Search className="w-4 h-4 mr-2 text-blue-600" />
          Similar Tickets Found ({similarTickets.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-gray-600 mb-3">
          Review these similar tickets before creating a new one to avoid duplicates:
        </div>

        {similarTickets.map((ticket) => (
          <div
            key={ticket.id}
            className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {ticket.title}
                </h4>
                <p className="text-xs text-gray-600 mt-1 line-clamp-2">
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
                <Badge variant={getStatusColor(ticket.status)} className="text-xs">
                  {formatStatus(ticket.status)}
                </Badge>
                <span className="text-xs text-gray-500">
                  {ticket.team_name}
                </span>
                <span className="text-xs text-gray-400 flex items-center">
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

        <div className="text-xs text-gray-500 pt-2 border-t">
          💡 Tip: If your issue is similar but different, mention the related ticket number in your description.
        </div>
      </CardContent>
    </Card>
  );
}