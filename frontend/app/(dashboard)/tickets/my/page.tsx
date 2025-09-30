'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Eye } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { TicketCreator } from '@/components/ui/ticket-creator';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus, TicketList } from '@/lib/types';
import { useAuthStore } from '@/lib/store/auth';

function MyTicketsContent() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('created');

  const { data: createdTickets, isLoading: isLoadingCreated } = useQuery({
    queryKey: ['tickets', 'created', user?.id],
    queryFn: () => apiClient.getTickets({
      created_by_me: true,
      page: 1,
      page_size: 20,
    }),
    enabled: !!user?.id,
  });

  const { data: assignedTickets, isLoading: isLoadingAssigned } = useQuery({
    queryKey: ['tickets', 'assigned', user?.id],
    queryFn: () => apiClient.getTickets({
      assignee_id: user!.id,
      page: 1,
      page_size: 20,
    }),
    enabled: !!user?.id,
  });

  const { data: commentedTickets, isLoading: isLoadingCommented } = useQuery({
    queryKey: ['tickets', 'commented', user?.id],
    queryFn: () => apiClient.getTickets({
      commented_by: user!.id,
      page: 1,
      page_size: 20,
    }),
    enabled: !!user?.id,
  });

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

  const renderTicketsTable = (tickets: TicketList | undefined, isLoading: boolean) => (
    <Card className="shadow-md">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Creator</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Comments</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tickets?.tickets?.map((ticket) => (
              <TableRow key={ticket.id}>
                <TableCell>
                  <div>
                    <p className="font-medium text-gray-900">{ticket.title}</p>
                    <p className="text-sm text-gray-500 truncate max-w-xs">
                      {ticket.description}
                    </p>
                    {ticket.tags && ticket.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ticket.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                        {ticket.tags.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{ticket.tags.length - 3}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-gray-600">
                    {ticket.team_name}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className={getStatusColor(ticket.status)}>
                    {formatStatus(ticket.status)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${getPriorityColor(ticket.priority)}`}></div>
                    <span className="text-sm capitalize">{formatPriority(ticket.priority)}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <TicketCreator ticket={ticket} showAvatar={true} />
                </TableCell>
                <TableCell>
                  <span className="text-sm text-gray-500">
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-gray-500">
                    {ticket.comment_count || 0}
                  </span>
                </TableCell>
                <TableCell>
                  <Link href={`/tickets/${ticket.id}`}>
                    <Button variant="ghost" size="sm">
                      <Eye className="w-4 h-4" />
                    </Button>
                  </Link>
                </TableCell>
              </TableRow>
            ))}
            {(!tickets?.tickets || tickets.tickets.length === 0) && (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <div className="text-gray-500">
                    {isLoading ? 'Loading tickets...' : 'No tickets found'}
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );

  return (
    <>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">My Tickets</h1>
        <p className="mt-2 text-gray-600">
          View and manage tickets related to you
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="shadow-md hover:shadow-lg transition-shadow">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Created by Me
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{createdTickets?.total || 0}</div>
          </CardContent>
        </Card>

        <Card className="shadow-md hover:shadow-lg transition-shadow">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Assigned to Me
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{assignedTickets?.total || 0}</div>
          </CardContent>
        </Card>

        <Card className="shadow-md hover:shadow-lg transition-shadow">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              I Commented On
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{commentedTickets?.total || 0}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="created">Created by Me</TabsTrigger>
          <TabsTrigger value="assigned">Assigned to Me</TabsTrigger>
          <TabsTrigger value="commented">I Commented On</TabsTrigger>
        </TabsList>

        <TabsContent value="created" className="mt-6">
          {renderTicketsTable(createdTickets, isLoadingCreated)}
        </TabsContent>

        <TabsContent value="assigned" className="mt-6">
          {renderTicketsTable(assignedTickets, isLoadingAssigned)}
        </TabsContent>

        <TabsContent value="commented" className="mt-6">
          {renderTicketsTable(commentedTickets, isLoadingCommented)}
        </TabsContent>
      </Tabs>
    </>
  );
}

export default function MyTicketsPage() {
  return (
    <DashboardLayout>
      <MyTicketsContent />
    </DashboardLayout>
  );
}