'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { Plus, Users, Settings, UserPlus } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { apiClient } from '@/lib/api';

const createTeamSchema = z.object({
  name: z.string().min(1, 'Team name is required').max(120, 'Team name must be less than 120 characters'),
  description: z.string().optional(),
});

type CreateTeamFormData = z.infer<typeof createTeamSchema>;

function TeamsContent() {
  const queryClient = useQueryClient();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.getTeams(),
  });

  const { data: teamMembers } = useQuery({
    queryKey: ['team-members', selectedTeam],
    queryFn: () => selectedTeam ? apiClient.getTeamMembers(selectedTeam) : null,
    enabled: !!selectedTeam,
  });

  const createTeamMutation = useMutation({
    mutationFn: (data: CreateTeamFormData) => apiClient.createTeam(data.name, data.description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      setIsCreateDialogOpen(false);
      createTeamForm.reset();
      toast.success('Team created successfully');
    },
    onError: () => {
      toast.error('Failed to create team');
    },
  });

  const createTeamForm = useForm<CreateTeamFormData>({
    resolver: zodResolver(createTeamSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const onCreateTeamSubmit = (data: CreateTeamFormData) => {
    createTeamMutation.mutate(data);
  };

  const formatRole = (role: string) => {
    return role.charAt(0).toUpperCase() + role.slice(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Teams</h1>
          <p className="mt-2 text-gray-600">
            Manage your teams and their members
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Team
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Team</DialogTitle>
              <DialogDescription>
                Create a new team to organize your tickets and collaborate with others.
              </DialogDescription>
            </DialogHeader>
            <Form {...createTeamForm}>
              <form onSubmit={createTeamForm.handleSubmit(onCreateTeamSubmit)} className="space-y-4">
                <FormField
                  control={createTeamForm.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Team Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter team name..." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={createTeamForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description (Optional)</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder="Describe what this team does..."
                          className="min-h-[80px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex justify-end space-x-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsCreateDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={createTeamMutation.isPending}>
                    {createTeamMutation.isPending ? 'Creating...' : 'Create Team'}
                  </Button>
                </div>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {teams?.map((team) => (
          <Card 
            key={team.id} 
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedTeam === team.id ? 'ring-2 ring-blue-500 shadow-md' : ''
            }`}
            onClick={() => setSelectedTeam(selectedTeam === team.id ? null : team.id)}
          >
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center">
                  <Users className="w-5 h-5 mr-2 text-blue-600" />
                  {team.name}
                </span>
                <Badge variant="secondary">
                  {team.members_count || 0} members
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm mb-3">
                {team.description || 'No description provided'}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  Created {new Date(team.created_at).toLocaleDateString()}
                </span>
                <div className="flex space-x-1">
                  <Button size="sm" variant="ghost">
                    <UserPlus className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="ghost">
                    <Settings className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {(!teams || teams.length === 0) && (
          <div className="col-span-full text-center py-12">
            <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No teams yet</h3>
            <p className="text-gray-600 mb-4">
              Get started by creating your first team to organize your tickets.
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Team
            </Button>
          </div>
        )}
      </div>

      {selectedTeam && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Users className="w-5 h-5 mr-2" />
              Team Members
              <Badge variant="secondary" className="ml-2">
                {teamMembers?.length || 0}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {teamMembers && teamMembers.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User ID</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {teamMembers.map((member) => (
                    <TableRow key={`${member.team_id}-${member.user_id}`}>
                      <TableCell className="font-medium">
                        User {member.user_id}
                      </TableCell>
                      <TableCell>
                        <Badge variant={member.role === 'manager' ? 'default' : 'secondary'}>
                          {formatRole(member.role)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : 'N/A'}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button size="sm" variant="outline">
                            Edit Role
                          </Button>
                          <Button size="sm" variant="outline">
                            Remove
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8">
                <Users className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600">This team has no members yet.</p>
                <Button className="mt-4" size="sm">
                  <UserPlus className="w-4 h-4 mr-2" />
                  Add Member
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}

export default function TeamsPage() {
  return (
    <DashboardLayout>
      <TeamsContent />
    </DashboardLayout>
  );
}