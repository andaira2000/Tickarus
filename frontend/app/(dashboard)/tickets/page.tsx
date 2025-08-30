'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search, Filter, Plus, Eye } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { TicketCreator } from '@/components/ui/ticket-creator';
import { apiClient } from '@/lib/api';
import { TicketFilters, TicketPriority, TicketStatus } from '@/lib/types';

function TicketsContent() {
  const [filters, setFilters] = useState<TicketFilters>({
    page: 1,
    page_size: 20,
  });

  const { data: tickets, isLoading } = useQuery({
    queryKey: ['tickets', filters],
    queryFn: () => apiClient.getTickets(filters),
  });

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.getTeams(),
  });

  const handleFilterChange = (key: keyof TicketFilters, value: string | number | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page when filtering
    }));
  };

  const handleSearch = (query: string) => {
    setFilters(prev => ({
      ...prev,
      q: query || undefined,
      page: 1,
    }));
  };

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

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">All Tickets</h1>
          <p className="mt-2 text-gray-600">
            Manage and track tickets across all teams
          </p>
        </div>
        <Link href="/tickets/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Ticket
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search tickets..."
                className="pl-10"
                value={filters.q || ''}
                onChange={(e) => handleSearch(e.target.value)}
              />
            </div>

            <Select value={filters.team_id || 'all'} onValueChange={(value) => 
              handleFilterChange('team_id', value === 'all' ? undefined : value)
            }>
              <SelectTrigger>
                <SelectValue placeholder="All Teams" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Teams</SelectItem>
                {teams?.map((team) => (
                  <SelectItem key={team.id} value={team.id}>
                    {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.status || 'all'} onValueChange={(value) => 
              handleFilterChange('status', value === 'all' ? undefined : value)
            }>
              <SelectTrigger>
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="in_review">In Review</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
                <SelectItem value="on_hold">On Hold</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filters.priority || 'all'} onValueChange={(value) => 
              handleFilterChange('priority', value === 'all' ? undefined : value)
            }>
              <SelectTrigger>
                <SelectValue placeholder="All Priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tickets Table */}
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

      {/* Pagination */}
      {tickets && tickets.total > tickets.page_size && (
        <div className="mt-6 flex justify-center">
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              disabled={filters.page === 1}
              onClick={() => handleFilterChange('page', (filters.page || 1) - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-gray-600">
              Page {filters.page || 1} of {Math.ceil(tickets.total / tickets.page_size)}
            </span>
            <Button
              variant="outline"
              disabled={(filters.page || 1) >= Math.ceil(tickets.total / tickets.page_size)}
              onClick={() => handleFilterChange('page', (filters.page || 1) + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

export default function TicketsPage() {
  return (
    <DashboardLayout>
      <TicketsContent />
    </DashboardLayout>
  );
}