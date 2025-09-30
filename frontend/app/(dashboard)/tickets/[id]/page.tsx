'use client';

import { use, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { ArrowLeft, MessageSquare, Clock, User, Tag, Bot } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Separator } from '@/components/ui/separator';
import { TicketCreator } from '@/components/ui/ticket-creator';
import { AIChat } from '@/components/ui/ai-chat';
import { AIAnalysis } from '@/components/ui/ai-analysis';
import { apiClient } from '@/lib/api';
import { Comment, TicketPriority, TicketStatus } from '@/lib/types';

const commentSchema = z.object({
  content: z.string().min(1, 'Comment cannot be empty'),
});

type CommentFormData = z.infer<typeof commentSchema>;

interface TicketDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

function TicketDetailContent({ ticketId }: { ticketId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);

  const { data: ticket, isLoading } = useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => apiClient.getTicket(ticketId),
  });

  const { data: comments } = useQuery({
    queryKey: ['comments', ticketId],
    queryFn: () => apiClient.getComments(ticketId),
  });

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.getTeams(),
  });

  const commentMutation = useMutation({
    mutationFn: (content: string) => apiClient.createComment(ticketId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', ticketId] });
      commentForm.reset();
      toast.success('Comment added successfully');
    },
    onError: () => {
      toast.error('Failed to add comment');
    },
  });

  const updateTicketMutation = useMutation({
    mutationFn: (updates: { status?: TicketStatus; priority?: TicketPriority; team_id?: string }) => 
      apiClient.updateTicket(ticketId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] });
      toast.success('Ticket updated successfully');
    },
    onError: () => {
      toast.error('Failed to update ticket');
    },
  });

  const commentForm = useForm<CommentFormData>({
    resolver: zodResolver(commentSchema),
    defaultValues: {
      content: '',
    },
  });

  const onCommentSubmit = (data: CommentFormData) => {
    commentMutation.mutate(data.content);
  };

  const handleStatusChange = (status: TicketStatus) => {
    updateTicketMutation.mutate({ status });
  };

  const handlePriorityChange = (priority: TicketPriority) => {
    updateTicketMutation.mutate({ priority });
  };

  const handleTeamChange = (teamId: string) => {
    updateTicketMutation.mutate({ team_id: teamId });
  };

  const getPriorityColor = (priority: TicketPriority) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
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

  const formatStatus = (status: TicketStatus) => {
    return status.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const formatPriority = (priority: TicketPriority) => {
    return priority.charAt(0).toUpperCase() + priority.slice(1);
  };

  const isAIAssistantComment = (comment: Comment) => {
    return comment.author_info?.system_user_type === 'ai_assistant';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900">Ticket not found</h2>
        <p className="mt-2 text-gray-600">The ticket you&apos;re looking for doesn&apos;t exist.</p>
        <Button onClick={() => router.push('/tickets')} className="mt-4">
          Back to Tickets
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <div className="flex-1">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">{ticket.title}</h1>

          <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
            <span>#{ticket.id.slice(-6)}</span>
            <span>•</span>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${getPriorityColor(ticket.priority)}`}></div>
              <span className="capitalize">{formatPriority(ticket.priority)} Priority</span>
            </div>
            <span>•</span>
            <Badge variant="secondary" className={getStatusColor(ticket.status)}>
              {formatStatus(ticket.status)}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4" />
                <span className="font-medium text-gray-700">Reporter:</span>
                <TicketCreator ticket={ticket} showAvatar={false} />
              </div>

              {ticket.assignee_id && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4" />
                    <span className="font-medium text-gray-700">Assignee:</span>
                    <span>User {ticket.assignee_id}</span>
                  </div>
                </>
              )}

              <span>•</span>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span className="font-medium text-gray-700">Created:</span>
                <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
              </div>

              {ticket.updated_at && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span className="font-medium text-gray-700">Updated:</span>
                    <span>{new Date(ticket.updated_at).toLocaleDateString()}</span>
                  </div>
                </>
              )}
            </div>

            <AIAnalysis ticketId={ticketId} onOpenChange={setIsAnalysisOpen} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <div
                  className={`whitespace-pre-wrap text-sm text-muted-foreground transition-all ${
                    !isDescriptionExpanded && ticket.description.length > 300
                      ? 'line-clamp-3'
                      : ''
                  }`}
                >
                  {ticket.description}
                </div>
                {ticket.description.length > 300 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
                    className="mt-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
                  >
                    {isDescriptionExpanded ? 'Show less' : 'Show more'}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center">
                <MessageSquare className="w-5 h-5 mr-2" />
                Comments ({comments?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {comments?.map((comment) => {
                  const isAI = isAIAssistantComment(comment);

                  if (isAI) {
                    return (
                      <div key={comment.id} className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-3">
                          <div className="w-6 h-6 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                            <Bot className="w-3 h-3 text-white" />
                          </div>
                          <span className="font-medium text-purple-700">
                            {comment.author_info?.display_name || 'Tickarus AI Assistant'}
                          </span>
                          <Badge variant="outline" className="border-purple-300 text-purple-700 text-xs">
                            AI Assistant
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {new Date(comment.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed text-justify px-2" style={{ textAlignLast: 'left' }}>
                          {(() => {
                            let processedContent = comment.content
                              .replace(/[🎯📋🔍💡✅❌⚠️🚀📊🔧⭐🤖🟢🟡🔴]/g, '')
                              .replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
                              .replace(/(?:^|\n)\s*(?:\*\*)?AI Root Cause Analysis(?:\*\*)?\s*(?:\n|$)/gi, '\n')
                              .replace(/(?:^|\n)\s*(?:\*\*)?Root Cause Analysis(?:\*\*)?\s*(?:\n|$)/gi, '\n')
                              .replace(/---.*?Analysis method:.*?(?:\n|$)/gi, '')
                              .replace(/.*?Analysis method:.*?(?:\n|$)/gi, '')
                              .replace(/^\s*---+\s*$/gm, '')
                              .replace(/^\s*---.*$/gm, '')
                              .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                              .replace(/#{1,6}\s(.*?)(?=\n|$)/g, '<strong>$1</strong>')
                              .replace(/^\s*[-*+]\s(.+)/gm, '<p class="mb-2">• $1</p>')
                              .replace(/^\s*(\d+)\.\s(.+)/gm, '<p class="mb-2">$1. $2</p>')
                              .replace(/`([^`]+)`/g, '$1') 
                              .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                              .replace(/\n\n+/g, '\n\n')
                              .trim();

                            const confidenceMatch = processedContent.match(/(?:^|\n)\s*(?:\*\*)?Confidence Level:?\s*([^(\n]*?)(?:\s*\(([^)]+)\))?(?:\n|$)/i);
                            let confidenceLevel = null;
                            if (confidenceMatch) {
                              const level = confidenceMatch[1].trim();
                              const percentage = confidenceMatch[2] ? confidenceMatch[2].trim() : null;

                              if (percentage) {
                                confidenceLevel = `${level} (${percentage.replace('%', '')}%)`;
                              } else {
                                confidenceLevel = level;
                              }

                              processedContent = processedContent.replace(/(?:^|\n)\s*(?:\*\*)?Confidence Level:?.*?(?:\n|$)/gi, '\n');
                            }

                            const mainContent = processedContent
                              .split('\n\n')
                              .map(paragraph => paragraph.trim())
                              .filter(paragraph => paragraph.length > 0)
                              .filter(paragraph => !paragraph.match(/^<p class="mb-2">/)) 
                              .map(paragraph => {
                                if (paragraph.includes('<p class="mb-2">')) {
                                  return paragraph;
                                }
                                return `<p class="mb-3">${paragraph}</p>`;
                              })
                              .join('');

                            return (
                              <>
                                {confidenceLevel && (
                                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                                    <div className="flex items-center gap-2">
                                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                                      <span className="text-xs font-medium text-blue-700">
                                        Confidence Level: {confidenceLevel}
                                      </span>
                                    </div>
                                  </div>
                                )}
                                <div dangerouslySetInnerHTML={{ __html: mainContent }} />
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={comment.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                      <div className="flex items-start space-x-3">
                        {/* Profile Avatar */}
                        <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center flex-shrink-0">
                          <span className="text-white text-sm font-medium">
                            {(comment.author_info?.display_name || 'U').charAt(0).toUpperCase()}
                          </span>
                        </div>

                        {/* Comment Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="font-medium text-slate-900">
                              {comment.author_info ? comment.author_info.display_name : 'Unknown User'}
                            </span>
                            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">
                              {new Date(comment.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                            {comment.content}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {(!comments || comments.length === 0) && (
                  <p className="text-muted-foreground text-center py-4">
                    No comments yet. Be the first to comment!
                  </p>
                )}
              </div>

              <Separator className="my-6" />

              <Form {...commentForm}>
                <form onSubmit={commentForm.handleSubmit(onCommentSubmit)} className="space-y-4">
                  <FormField
                    control={commentForm.control}
                    name="content"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Add Comment</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Add a comment..."
                            className="min-h-[100px]"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button
                    type="submit"
                    disabled={commentMutation.isPending}
                    size="sm"
                  >
                    {commentMutation.isPending ? 'Adding...' : 'Add Comment'}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 sticky top-6 self-start max-h-[calc(100vh-8rem)] overflow-y-auto">
          <Card className="shadow-md">
            <CardContent className="p-5">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block text-gray-700">Status</label>
                  <Select
                    value={ticket.status}
                    onValueChange={(value: TicketStatus) => handleStatusChange(value)}
                  >
                    <SelectTrigger className="h-9 w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="in_review">In Review</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                      <SelectItem value="blocked">Blocked</SelectItem>
                      <SelectItem value="on_hold">On Hold</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block text-gray-700">Priority</label>
                  <Select
                    value={ticket.priority}
                    onValueChange={(value: TicketPriority) => handlePriorityChange(value)}
                  >
                    <SelectTrigger className="h-9 w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block text-gray-700">Team</label>
                  <Select
                    value={ticket.team_id}
                    onValueChange={(value: string) => handleTeamChange(value)}
                  >
                    <SelectTrigger className="h-9 w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {teams?.map((team) => (
                        <SelectItem key={team.id} value={team.id}>
                          {team.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {ticket.tags && ticket.tags.length > 0 && (
                  <div>
                    <label className="text-sm font-medium mb-2 block text-gray-700">Tags</label>
                    <div className="flex flex-wrap gap-2">
                      {ticket.tags.map((tag) => (
                        <Badge key={tag} variant="outline">
                          <Tag className="w-3 h-3 mr-1" />
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {!isAnalysisOpen && <AIChat ticketId={ticketId} />}
    </>
  );
}

export default function TicketDetailPage({ params }: TicketDetailPageProps) {
  const resolvedParams = use(params);
  return (
    <DashboardLayout>
      <TicketDetailContent ticketId={resolvedParams.id} />
    </DashboardLayout>
  );
}