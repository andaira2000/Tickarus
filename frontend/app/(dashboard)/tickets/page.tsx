'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search, Filter, Plus, Eye, SortAsc, SortDesc, Clock, User, MessageSquare } from 'lucide-react';

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
  const [sortBy, setSortBy] = useState<string>('created');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

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

  const getStatusCounts = () => {
    const counts = tickets?.tickets?.reduce((acc, ticket) => {
      acc[ticket.status] = (acc[ticket.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>) || {};

    return {
      all: tickets?.total || 0,
      open: counts.open || 0,
      in_progress: counts.in_progress || 0,
      resolved: counts.resolved || 0,
      closed: counts.closed || 0
    };
  };

  const statusCounts = getStatusCounts();

  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
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

      {/* Header with counts */}
      <div className="flex flex-wrap gap-4 mb-6">
        <Badge variant="outline" className="px-3 py-1">
          All: {statusCounts.all}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-blue-50 text-blue-700 border-blue-200">
          Open: {statusCounts.open}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-yellow-50 text-yellow-700 border-yellow-200">
          In Progress: {statusCounts.in_progress}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-green-50 text-green-700 border-green-200">
          Resolved: {statusCounts.resolved}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-green-50 text-green-700 border-green-200">
          Closed: {statusCounts.closed}
        </Badge>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search tickets by title, description, tags, or reporter..."
            value={filters.q || ''}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex gap-2">
          <Select value={filters.team_id || 'all'} onValueChange={(value) =>
            handleFilterChange('team_id', value === 'all' ? undefined : value)
          }>
            <SelectTrigger className="w-[140px]">
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
            <SelectTrigger className="w-[140px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="in_review">In Review</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filters.priority || 'all'} onValueChange={(value) =>
            handleFilterChange('priority', value === 'all' ? undefined : value)
          }>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priority</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="created">Created</SelectItem>
              <SelectItem value="updated">Updated</SelectItem>
              <SelectItem value="title">Title</SelectItem>
              <SelectItem value="priority">Priority</SelectItem>
              <SelectItem value="status">Status</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="outline" size="icon" onClick={toggleSortOrder}>
            {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Results count */}
      <div className="text-sm text-muted-foreground mb-4">
        Showing {tickets?.tickets?.length || 0} of {tickets?.total || 0} tickets
      </div>

      {/* Tickets List */}
      <div className="space-y-4">
        {tickets?.tickets?.map((ticket) => (
          <Card key={ticket.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => window.location.href = `/tickets/${ticket.id}`}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="mb-2 text-lg font-medium">{ticket.title}</h3>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className={`w-2 h-2 rounded-full ${getPriorityColor(ticket.priority)}`}></div>
                    <span className="capitalize">{formatPriority(ticket.priority)} Priority</span>
                    <span>•</span>
                    <Badge variant="secondary" className={getStatusColor(ticket.status)}>
                      {formatStatus(ticket.status)}
                    </Badge>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  #{ticket.id.slice(-6)}
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                {ticket.description}
              </p>

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    <span>{ticket.creator_name || 'Unknown'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span>Team: {ticket.team_name}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />
                  <span>{ticket.comments_count || 0} comments</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {(!tickets?.tickets || tickets.tickets.length === 0) && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg mb-2">No tickets found</h3>
            <p className="text-muted-foreground">
              {isLoading ? 'Loading tickets...' : 'Try adjusting your search or filters'}
            </p>
          </div>
        )}
      </div>

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