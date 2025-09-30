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
  ThumbsDown,
  X,
  ChevronRight
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
  onOpenChange?: (isOpen: boolean) => void;
}

export function AIAnalysis({ ticketId, className, onOpenChange }: AIAnalysisProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    onOpenChange?.(open);
  };
  const [userRating, setUserRating] = useState<'helpful' | 'not_helpful' | null>(null);
  const queryClient = useQueryClient();

  const { data: analysis, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-analysis', ticketId],
    queryFn: () => apiClient.getAIRootCauseAnalysis(ticketId),
    enabled: isOpen,
    staleTime: 300000,
  });

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

  return (
    <>
      <Button
        onClick={() => handleOpenChange(true)}
        className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 shadow-md"
        size="sm"
      >
        <Brain className="w-4 h-4 mr-2" />
        AI Analysis
        <ChevronRight className="w-4 h-4 ml-1" />
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-50 transition-opacity"
            onClick={() => handleOpenChange(false)}
          />
          <div className="fixed inset-y-0 right-0 w-[600px] bg-white shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-6 border-b bg-gradient-to-r from-purple-500 to-blue-500">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center">
                  <Brain className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">AI Root Cause Analysis</h2>
                  {analysis && (
                    <Badge variant="secondary" className="text-xs bg-white/20 text-white border-0 mt-1">
                      {analysis.llm_used ? 'LLM-powered' : 'Pattern-based'}
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {analysis && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => refetch()}
                    disabled={isLoading}
                    className="text-white hover:bg-white/20"
                    title="Refresh analysis"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleOpenChange(false)}
                  className="text-white hover:bg-white/20"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {isLoading && (
                <div className="space-y-4">
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-8 h-8 animate-spin text-purple-600 mr-3" />
                    <span className="text-lg text-gray-600">
                      AI is analyzing this ticket...
                    </span>
                  </div>
                  <div className="space-y-3">
                    <Skeleton className="h-6 w-full" />
                    <Skeleton className="h-6 w-3/4" />
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                  </div>
                </div>
              )}

              {error && (
                <div className="text-center py-12">
                  <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <p className="text-lg font-semibold text-gray-900 mb-2">
                    Failed to generate analysis
                  </p>
                  <p className="text-sm text-gray-600 mb-4">
                    This might be due to insufficient context or a temporary error.
                  </p>
                  <Button onClick={() => refetch()} variant="outline">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Try Again
                  </Button>
                </div>
              )}

              {analysis && !isLoading && (
                <div className="space-y-6">
                  <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg border border-purple-200">
                    <div className="flex items-center">
                      <span className="text-2xl mr-3">
                        {getConfidenceEmoji(analysis.confidence_score)}
                      </span>
                      <div>
                        <div className="text-sm font-medium text-gray-700">Confidence Level</div>
                        <div className="flex items-center gap-2">
                          <span className={`text-lg font-bold ${getConfidenceColor(analysis.confidence_score)}`}>
                            {getConfidenceLabel(analysis.confidence_score)}
                          </span>
                          <span className="text-sm text-gray-500">
                            ({Math.round(analysis.confidence_score * 100)}%)
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-gray-900 mb-3 flex items-center text-lg">
                      <AlertTriangle className="w-5 h-5 mr-2 text-orange-600" />
                      Root Cause
                    </h3>
                    <div className="bg-orange-50 border-l-4 border-orange-400 rounded-r-lg p-4">
                      <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                        {analysis.root_cause}
                      </p>
                    </div>
                  </div>

                  {analysis.suggestions && analysis.suggestions.length > 0 && (
                    <div>
                      <h3 className="font-bold text-gray-900 mb-3 flex items-center text-lg">
                        <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
                        Recommended Actions
                      </h3>
                      <div className="bg-green-50 border-l-4 border-green-400 rounded-r-lg p-4">
                        <ol className="space-y-3">
                          {analysis.suggestions.map((suggestion, index) => (
                            <li key={index} className="flex items-start">
                              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-bold mr-3 mt-0.5">
                                {index + 1}
                              </span>
                              <span className="text-gray-800 leading-relaxed">{suggestion}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  )}

                  {analysis.similar_resolved_tickets && analysis.similar_resolved_tickets.length > 0 && (
                    <div>
                      <h3 className="font-bold text-gray-900 mb-3 flex items-center text-lg">
                        <ExternalLink className="w-5 h-5 mr-2 text-blue-600" />
                        Similar Resolved Issues
                      </h3>
                      <div className="space-y-3">
                        {analysis.similar_resolved_tickets.slice(0, 3).map((ticket, index) => (
                          <div
                            key={index}
                            className="flex items-start justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg hover:shadow-md transition-shadow"
                          >
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-blue-900 mb-1">
                                #{ticket.id.slice(0, 8)}...
                              </p>
                              <p className="text-sm text-gray-700 mb-2">{ticket.title}</p>
                              {ticket.resolution && (
                                <p className="text-sm text-blue-700 italic">
                                  Resolution: {ticket.resolution}
                                </p>
                              )}
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="ml-3 flex-shrink-0"
                              onClick={() => window.open(`/tickets/${ticket.id}`, '_blank')}
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {analysis && !isLoading && (
              <div className="border-t bg-gray-50 p-6 space-y-4">
                <div className="text-xs text-gray-500">
                  Analysis method: {analysis.analysis_method} • Generated at {new Date().toLocaleString()}
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-700">
                    Was this analysis helpful?
                  </span>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant={userRating === 'helpful' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleRateAnalysis('helpful')}
                      disabled={rateAnalysisMutation.isPending}
                      className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white"
                    >
                      <ThumbsUp className="w-4 h-4 mr-1" />
                      Yes
                    </Button>
                    <Button
                      variant={userRating === 'not_helpful' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleRateAnalysis('not_helpful')}
                      disabled={rateAnalysisMutation.isPending}
                    >
                      <ThumbsDown className="w-4 h-4 mr-1" />
                      No
                    </Button>
                  </div>
                </div>

                {userRating && (
                  <div className="text-sm text-green-600 text-center font-medium">
                    Thank you for your feedback! This helps improve our AI analysis.
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}