'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, Tag, Zap, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/lib/api';
import { TicketPriority } from '@/lib/types';

interface AutoTaggingSuggestionsProps {
  title: string;
  description: string;
  onTagsSelected?: (tags: string[]) => void;
  onPrioritySelected?: (priority: TicketPriority) => void;
  selectedTags?: string[];
  selectedPriority?: TicketPriority;
  className?: string;
}

export function AutoTaggingSuggestions({
  title,
  description,
  onTagsSelected,
  onPrioritySelected,
  selectedTags = [],
  selectedPriority,
  className,
}: AutoTaggingSuggestionsProps) {
  const [debouncedText, setDebouncedText] = useState('');
  const [appliedSuggestions, setAppliedSuggestions] = useState(false);

  // Debounce the input to avoid too many API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      const combinedText = `${title} ${description}`.trim();
      if (combinedText.length > 10) {
        setDebouncedText(combinedText);
        setAppliedSuggestions(false); // Reset when text changes
      } else {
        setDebouncedText('');
      }
    }, 800);

    return () => clearTimeout(timer);
  }, [title, description]);

  // Query auto-tagging suggestions
  const { data: suggestions, isLoading, error } = useQuery({
    queryKey: ['auto-tagging', debouncedText],
    queryFn: () => apiClient.getAutoTaggingSuggestions(title, description),
    enabled: debouncedText.length > 0,
    staleTime: 60000, // Cache for 1 minute
  });

  const handleApplyTags = () => {
    if (suggestions?.suggested_tags && onTagsSelected) {
      const newTags = [...new Set([...selectedTags, ...suggestions.suggested_tags])];
      onTagsSelected(newTags);
      setAppliedSuggestions(true);
    }
  };

  const handleApplyPriority = () => {
    if (suggestions?.suggested_priority && onPrioritySelected) {
      onPrioritySelected(suggestions.suggested_priority as TicketPriority);
      setAppliedSuggestions(true);
    }
  };

  const handleApplyAll = () => {
    handleApplyTags();
    handleApplyPriority();
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'destructive';
      case 'high':
        return 'default';
      case 'medium':
        return 'secondary';
      case 'low':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const formatPriority = (priority: string) => {
    return priority.charAt(0).toUpperCase() + priority.slice(1);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'High Confidence';
    if (score >= 0.6) return 'Medium Confidence';
    return 'Low Confidence';
  };

  if (debouncedText.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <Sparkles className="w-4 h-4 mr-2 text-gray-400" />
            AI Auto-Tagging
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Start typing a title and description to get AI-powered tag and priority suggestions...
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
            <Loader2 className="w-4 h-4 mr-2 animate-spin text-blue-600" />
            Analyzing Content...
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Skeleton className="h-4 w-24 mb-2" />
            <div className="flex space-x-2">
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-18" />
            </div>
          </div>
          <div>
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-6 w-24" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center text-sm font-medium">
            <Sparkles className="w-4 h-4 mr-2 text-red-600" />
            Auto-Tagging Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Unable to generate suggestions. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!suggestions) {
    return null;
  }

  const hasTagSuggestions = suggestions.suggested_tags?.length > 0;
  const hasPrioritySuggestion = !!suggestions.suggested_priority;
  const averageConfidence = suggestions.confidence_scores
    ? Object.values(suggestions.confidence_scores).reduce((a, b) => a + b, 0) / Object.values(suggestions.confidence_scores).length
    : 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-sm font-medium">
          <div className="flex items-center">
            <Sparkles className="w-4 h-4 mr-2 text-purple-600" />
            AI Suggestions
          </div>
          {averageConfidence > 0 && (
            <span className={`text-xs ${getConfidenceColor(averageConfidence)}`}>
              {getConfidenceLabel(averageConfidence)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasTagSuggestions && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                <Tag className="w-3 h-3 mr-1" />
                Suggested Tags
              </label>
              {onTagsSelected && !appliedSuggestions && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleApplyTags}
                  className="text-xs h-6 px-2"
                >
                  Apply
                </Button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestions.suggested_tags.map((tag) => {
                const isSelected = selectedTags.includes(tag);
                const confidence = suggestions.confidence_scores?.[tag] || 0;
                return (
                  <Badge
                    key={tag}
                    variant={isSelected ? "default" : "outline"}
                    className="text-xs cursor-pointer hover:bg-gray-100"
                    onClick={() => {
                      if (onTagsSelected) {
                        const newTags = isSelected
                          ? selectedTags.filter(t => t !== tag)
                          : [...selectedTags, tag];
                        onTagsSelected(newTags);
                      }
                    }}
                  >
                    {tag}
                    {confidence > 0 && (
                      <span className={`ml-1 ${getConfidenceColor(confidence)}`}>
                        ({Math.round(confidence)}%)
                      </span>
                    )}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {hasPrioritySuggestion && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                <Zap className="w-3 h-3 mr-1" />
                Suggested Priority
              </label>
              {onPrioritySelected && !appliedSuggestions && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleApplyPriority}
                  className="text-xs h-6 px-2"
                >
                  Apply
                </Button>
              )}
            </div>
            <Badge
              variant={
                selectedPriority === suggestions.suggested_priority
                  ? getPriorityColor(suggestions.suggested_priority)
                  : "outline"
              }
              className="cursor-pointer hover:bg-gray-100"
              onClick={() => {
                if (onPrioritySelected) {
                  onPrioritySelected(suggestions.suggested_priority as TicketPriority);
                }
              }}
            >
              {formatPriority(suggestions.suggested_priority)}
              {suggestions.confidence_scores?.[`priority_${suggestions.suggested_priority}`] && (
                <span className={`ml-1 ${getConfidenceColor(suggestions.confidence_scores[`priority_${suggestions.suggested_priority}`])}`}>
                  ({Math.round(suggestions.confidence_scores[`priority_${suggestions.suggested_priority}`])}%)
                </span>
              )}
            </Badge>
          </div>
        )}

        {(hasTagSuggestions || hasPrioritySuggestion) && !appliedSuggestions && (
          <div className="pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={handleApplyAll}
              className="w-full text-xs"
            >
              <Sparkles className="w-3 h-3 mr-1" />
              Apply All Suggestions
            </Button>
          </div>
        )}

        {appliedSuggestions && (
          <div className="text-xs text-green-600 text-center py-2 bg-green-50 rounded">
            ✓ AI suggestions applied! You can still modify tags and priority manually.
          </div>
        )}

        <div className="text-xs text-gray-500 pt-2 border-t">
          💡 These suggestions are based on similar tickets and common patterns.
        </div>
      </CardContent>
    </Card>
  );
}