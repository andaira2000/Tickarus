'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Badge } from '@/components/ui/badge';
import { SimilaritySuggestions } from '@/components/ui/similarity-suggestions';
import { AutoTaggingSuggestions } from '@/components/ui/auto-tagging';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus } from '@/lib/types';

const createTicketSchema = z.object({
  title: z.string().min(1, 'Title is required').max(280, 'Title must be less than 280 characters'),
  description: z.string().min(1, 'Description is required'),
  team_id: z.string().min(1, 'Please select a team'),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  status: z.enum(['open', 'in_progress', 'in_review', 'resolved', 'closed', 'blocked', 'on_hold']).optional(),
  assignee_id: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

type CreateTicketFormData = z.infer<typeof createTicketSchema>;

function CreateTicketContent() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.getTeams(),
  });

  const form = useForm<CreateTicketFormData>({
    resolver: zodResolver(createTicketSchema),
    defaultValues: {
      title: '',
      description: '',
      team_id: '',
      priority: 'medium',
      status: 'open',
      assignee_id: '',
      tags: [],
    },
  });

  const onSubmit = async (data: CreateTicketFormData) => {
    setIsSubmitting(true);
    try {
      const ticketData = {
        title: data.title,
        description: data.description,
        team_id: data.team_id,
        priority: data.priority as TicketPriority,
        status: data.status as TicketStatus || 'open',
        assignee_id: data.assignee_id || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      };

      const newTicket = await apiClient.createTicket(ticketData);
      toast.success('Ticket created successfully!');
      router.push(`/tickets/${newTicket.id}`);
    } catch (error) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create ticket'
        : 'Failed to create ticket';
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Create New Ticket</h1>
        <p className="mt-2 text-gray-600">
          Create a new ticket to track issues, bugs, or feature requests.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Ticket Information</CardTitle>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Brief description of the issue..."
                        className="bg-input-background"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      A clear, concise title that summarizes the issue or request.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Provide detailed information about the issue, including steps to reproduce, expected behavior, and any relevant context..."
                        className="min-h-[120px] bg-input-background"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Detailed description of the issue, including steps to reproduce if applicable.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="team_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Team</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-input-background">
                            <SelectValue placeholder="Select a team" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {teams?.map((team) => (
                            <SelectItem key={team.id} value={team.id}>
                              {team.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        Which team should handle this ticket?
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="bg-input-background">
                            <SelectValue placeholder="Select priority" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                          <SelectItem value="critical">Critical</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        How urgent is this issue?
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <AutoTaggingSuggestions
                title={form.watch('title') || ''}
                description={form.watch('description') || ''}
                selectedTags={selectedTags}
                selectedPriority={form.watch('priority') as TicketPriority}
                onTagsSelected={setSelectedTags}
                onPrioritySelected={(priority) => form.setValue('priority', priority)}
              />

              {/* Selected Tags Display */}
              {selectedTags.length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Selected Tags
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {selectedTags.map((tag, index) => (
                      <Badge
                        key={index}
                        variant="default"
                        className="cursor-pointer"
                        onClick={() => {
                          setSelectedTags(selectedTags.filter((_, i) => i !== index));
                        }}
                      >
                        {tag} ×
                      </Badge>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Click on a tag to remove it
                  </p>
                </div>
              )}

                  <div className="flex items-center justify-between pt-6">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => router.back()}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? 'Creating...' : 'Create Ticket'}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>

        <div>
          <SimilaritySuggestions
            title={form.watch('title') || ''}
            description={form.watch('description') || ''}
          />
        </div>
      </div>
    </>
  );
}

export default function CreateTicketPage() {
  return (
    <DashboardLayout>
      <CreateTicketContent />
    </DashboardLayout>
  );
}