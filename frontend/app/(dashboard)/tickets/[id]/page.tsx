'use client';

import { use } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { ArrowLeft, MessageSquare, Clock, User } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Separator } from '@/components/ui/separator';
import { TicketCreator, TicketCreatorBadge } from '@/components/ui/ticket-creator';
import { AIChat } from '@/components/ui/ai-chat';
import { AIAnalysis } from '@/components/ui/ai-analysis';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus } from '@/lib/types';

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
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{ticket.title}</h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
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
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap text-sm text-muted-foreground">
                {ticket.description}
              </div>
            </CardContent>
          </Card>

          {/* Comments */}
          <Card className="shadow-md">
            <CardHeader>
              <CardTitle className="flex items-center">
                <MessageSquare className="w-5 h-5 mr-2" />
                Comments ({comments?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {comments?.map((comment) => (
                  <div key={comment.id} className="border-l-2 border-gray-200 pl-4">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="font-medium text-gray-900">
                        {comment.author_info ? comment.author_info.display_name : 'Unknown User'}
                      </span>
                      <span className="text-sm text-gray-500">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {comment.content}
                    </div>
                  </div>
                ))}

                {(!comments || comments.length === 0) && (
                  <p className="text-muted-foreground text-center py-4">
                    No comments yet. Be the first to comment!
                  </p>
                )}
              </div>

              <Separator className="my-6" />

              {/* Add Comment Form */}
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

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status and Priority */}
          <Card className="shadow-md">
            <CardContent className="space-y-4 p-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <Select
                    value={ticket.status}
                    onValueChange={(value: TicketStatus) => handleStatusChange(value)}
                  >
                    <SelectTrigger>
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
                  <label className="text-sm font-medium mb-2 block">Priority</label>
                  <Select
                    value={ticket.priority}
                    onValueChange={(value: TicketPriority) => handlePriorityChange(value)}
                  >
                    <SelectTrigger>
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
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Team</label>
                <Select
                  value={ticket.team_id}
                  onValueChange={(value: string) => handleTeamChange(value)}
                >
                  <SelectTrigger>
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
            </CardContent>
          </Card>

          {/* Ticket Info */}
          <Card className="shadow-md">
            <CardContent className="space-y-3 p-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">Reporter</span>
                  </div>
                  <div className="ml-6">
                    <TicketCreator ticket={ticket} showAvatar={true} />
                  </div>
                </div>

                {ticket.assignee_id && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-muted-foreground" />
                      <span className="font-medium">Assignee</span>
                    </div>
                    <p className="text-muted-foreground ml-6">User {ticket.assignee_id}</p>
                  </div>
                )}

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">Created</span>
                  </div>
                  <p className="text-muted-foreground ml-6">
                    {new Date(ticket.created_at).toLocaleDateString()} at {new Date(ticket.created_at).toLocaleTimeString()}
                  </p>
                </div>

                {ticket.updated_at && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="font-medium">Updated</span>
                    </div>
                    <p className="text-muted-foreground ml-6">
                      {new Date(ticket.updated_at).toLocaleDateString()} at {new Date(ticket.updated_at).toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* AI Analysis */}
          <AIAnalysis ticketId={ticketId} />

          {/* AI Chat */}
          <AIChat ticketId={ticketId} />
        </div>
      </div>
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