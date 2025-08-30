'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Plus, Eye } from 'lucide-react';

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
      created_by: user!.id,
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

  const formatStatus = (status: TicketStatus) => {
    return status.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const formatPriority = (priority: TicketPriority) => {
    return priority.charAt(0).toUpperCase() + priority.slice(1);
  };

  const renderTicketsTable = (tickets: TicketList | undefined, isLoading: boolean) => (
    <Card>
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
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-gray-600">
                    {ticket.team_name}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant={getStatusColor(ticket.status)}>
                    {formatStatus(ticket.status)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={getPriorityColor(ticket.priority)}>
                    {formatPriority(ticket.priority)}
                  </Badge>
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
                    {ticket.comments_count || 0}
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
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Tickets</h1>
          <p className="mt-2 text-gray-600">
            View and manage tickets related to you
          </p>
        </div>
        <Link href="/tickets/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Ticket
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Created by Me
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{createdTickets?.total || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Assigned to Me
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{assignedTickets?.total || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
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

      {/* Tickets Tabs */}
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