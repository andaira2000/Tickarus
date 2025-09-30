'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  Loader2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  ExternalLink,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';

interface AIAnalysisProps {
  ticketId: string;
  className?: string;
}

export function AIAnalysis({ ticketId, className }: AIAnalysisProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [userRating, setUserRating] = useState<'helpful' | 'not_helpful' | null>(null);
  const queryClient = useQueryClient();

  // Query AI analysis
  const { data: analysis, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-analysis', ticketId],
    queryFn: () => apiClient.getAIRootCauseAnalysis(ticketId),
    enabled: isExpanded,
    staleTime: 300000, // Cache for 5 minutes
  });

  // Rate analysis mutation
  const rateAnalysisMutation = useMutation({
    mutationFn: (rating: 'helpful' | 'not_helpful') =>
      apiClient.rateAIAnalysis(ticketId, rating),
    onSuccess: (_, rating) => {
      setUserRating(rating);
      toast.success('Thanks for your feedback!');
    },
    onError: () => {
      toast.error('Failed to submit rating');
    },
  });

  const handleRateAnalysis = (rating: 'helpful' | 'not_helpful') => {
    rateAnalysisMutation.mutate(rating);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceEmoji = (score: number) => {
    if (score >= 0.8) return '🟢';
    if (score >= 0.5) return '🟡';
    return '🔴';
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
  };

  if (!isExpanded) {
    return (
      <Card className={`shadow-md ${className}`}>
        <CardContent className="p-6">
          <div className="bg-purple-50 p-4 rounded-lg">
            <h4 className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-purple-600" />
              AI Root Cause Analysis
            </h4>
            <p className="text-sm text-muted-foreground mb-3">
              Get AI-powered analysis of potential root causes and solutions for this ticket.
            </p>
            <Button
              onClick={() => setIsExpanded(true)}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
              variant="default"
            >
              <Brain className="w-4 h-4 mr-2" />
              Analyze Ticket
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className={`shadow-md ${className}`}>
        <CardContent className="p-6">
          <div className="bg-purple-50 p-4 rounded-lg">
            <h4 className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-purple-600" />
              AI Root Cause Analysis
            </h4>
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-6 h-6 animate-spin text-purple-600 mr-2" />
              <span className="text-sm text-muted-foreground">
                AI is analyzing this ticket...
              </span>
            </div>
            <div className="space-y-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-20 w-full" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center">
              <Brain className="w-5 h-5 mr-2 text-purple-600" />
              AI Root Cause Analysis
            </div>
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetch()}
                disabled={isLoading}
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(false)}
              >
                ×
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600 mb-3">
              Failed to generate analysis. This might be due to insufficient context or a temporary error.
            </p>
            <Button onClick={() => refetch()} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!analysis) {
    return null;
  }

  return (
    <Card className={`shadow-md ${className}`}>
      <CardContent className="p-6">
        <div className="bg-purple-50 p-4 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-600" />
              AI Root Cause Analysis
              <Badge variant="outline" className="border-purple-300 text-purple-700">
                {analysis.llm_used ? 'LLM-powered' : 'Pattern-based'}
              </Badge>
            </h4>
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetch()}
                disabled={isLoading}
                title="Refresh analysis"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(false)}
              >
                ×
              </Button>
            </div>
          </div>

          {/* Confidence Level */}
          <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-purple-200">
          <div className="flex items-center">
            <span className="text-lg mr-2">
              {getConfidenceEmoji(analysis.confidence_score)}
            </span>
            <div>
              <span className="text-sm font-medium">Confidence Level: </span>
              <span className={`font-semibold ${getConfidenceColor(analysis.confidence_score)}`}>
                {getConfidenceLabel(analysis.confidence_score)}
              </span>
              <span className="text-gray-500 text-sm ml-1">
                ({Math.round(analysis.confidence_score * 100)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Root Cause */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
            <AlertTriangle className="w-4 h-4 mr-2 text-orange-600" />
            Root Cause
          </h4>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <p className="text-gray-800 whitespace-pre-wrap">
              {analysis.root_cause}
            </p>
          </div>
        </div>

        {/* Recommended Actions */}
        {analysis.suggestions && analysis.suggestions.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
              Recommended Actions
            </h4>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <ol className="space-y-2">
                {analysis.suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start">
                    <span className="font-medium text-green-700 mr-2 flex-shrink-0">
                      {index + 1}.
                    </span>
                    <span className="text-gray-800">{suggestion}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}

        {/* Similar Resolved Tickets */}
        {analysis.similar_resolved_tickets && analysis.similar_resolved_tickets.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
              <ExternalLink className="w-4 h-4 mr-2 text-blue-600" />
              Similar Resolved Issues
            </h4>
            <div className="space-y-2">
              {analysis.similar_resolved_tickets.slice(0, 3).map((ticket, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-blue-50 border border-blue-200 rounded text-sm"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-blue-900 truncate">
                      #{ticket.id.slice(0, 8)}... - {ticket.title}
                    </p>
                    {ticket.resolution && (
                      <p className="text-blue-700 text-xs mt-1 line-clamp-2">
                        Resolution: {ticket.resolution}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs h-6 px-2 ml-2"
                    onClick={() => window.open(`/tickets/${ticket.id}`, '_blank')}
                  >
                    <ExternalLink className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        <Separator />

        {/* Analysis Metadata & Rating */}
        <div className="space-y-3">
          <div className="text-xs text-gray-500">
            Analysis method: {analysis.analysis_method} •
            Generated at {new Date().toLocaleString()}
          </div>

          {/* User Rating */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              Was this analysis helpful?
            </span>
            <div className="flex items-center space-x-2">
              <Button
                variant={userRating === 'helpful' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleRateAnalysis('helpful')}
                disabled={rateAnalysisMutation.isPending}
                className="text-xs"
              >
                <ThumbsUp className="w-3 h-3 mr-1" />
                Yes
              </Button>
              <Button
                variant={userRating === 'not_helpful' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleRateAnalysis('not_helpful')}
                disabled={rateAnalysisMutation.isPending}
                className="text-xs"
              >
                <ThumbsDown className="w-3 h-3 mr-1" />
                No
              </Button>
            </div>
          </div>

          {userRating && (
            <div className="text-xs text-green-600 text-center">
              Thank you for your feedback! This helps improve our AI analysis.
            </div>
          )}
        </div>
        </div>
      </CardContent>
    </Card>
  );
}