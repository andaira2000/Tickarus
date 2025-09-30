'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, SortAsc, SortDesc, List, User, Tag, Clock, AlertCircle, CheckCircle, ChevronLeft, ChevronRight, Users } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TicketCreator } from '@/components/ui/ticket-creator';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus } from '@/lib/types';
import { useAuthStore } from '@/lib/store/auth';

function TicketsContent() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('created');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 1500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const buildFilters = (extraFilters = {}) => ({
    page: currentPage,
    page_size: pageSize,
    search_query: debouncedSearchQuery || undefined,
    status: statusFilter !== 'all' ? (statusFilter as TicketStatus) : undefined,
    priority: priorityFilter !== 'all' ? (priorityFilter as TicketPriority) : undefined,
    ...extraFilters,
  });

  const { data: allTicketsData, isLoading: isLoadingAll } = useQuery({
    queryKey: ['tickets', 'all', currentPage, debouncedSearchQuery, statusFilter, priorityFilter],
    queryFn: () => apiClient.getTickets(buildFilters()),
    enabled: activeTab === 'all',
  });

  const { data: myCreatedTickets, isLoading: isLoadingCreated } = useQuery({
    queryKey: ['tickets', 'created', user?.id, currentPage, debouncedSearchQuery, statusFilter, priorityFilter],
    queryFn: () => apiClient.getTickets(buildFilters({
      created_by_me: true,
    })),
    enabled: !!user?.id && activeTab === 'my',
  });

  const { data: myAssignedTickets, isLoading: isLoadingAssigned } = useQuery({
    queryKey: ['tickets', 'assigned', user?.id, currentPage, debouncedSearchQuery, statusFilter, priorityFilter],
    queryFn: () => apiClient.getTickets(buildFilters({
      assignee_id: user!.id,
    })),
    enabled: !!user?.id && activeTab === 'my',
  });

  const currentData = useMemo(() => {
    if (activeTab === 'my') {
      return myCreatedTickets;
    }
    return allTicketsData;
  }, [activeTab, allTicketsData, myCreatedTickets]);

  const currentTickets = useMemo(() => {
    return currentData?.tickets || [];
  }, [currentData]);

  const filteredAndSortedTickets = useMemo(() => {
    const sorted = [...currentTickets].sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();

      if (sortOrder === 'desc') {
        return dateB - dateA;
      } else {
        return dateA - dateB;
      }
    });
    return sorted;
  }, [currentTickets, sortOrder]);

  const { data: allTicketsCount } = useQuery({
    queryKey: ['tickets', 'count', 'all'],
    queryFn: () => apiClient.getTickets({ page: 1, page_size: 1 }),
  });

  const { data: myTicketsCount } = useQuery({
    queryKey: ['tickets', 'count', 'my', user?.id],
    queryFn: () => apiClient.getTickets({ created_by_me: true, page: 1, page_size: 1 }),
    enabled: !!user?.id,
  });

  const ticketCounts = useMemo(() => {
    const allCount = allTicketsCount?.total || 0;
    const myCount = myTicketsCount?.total || 0;
    return { all: allCount, my: myCount };
  }, [allTicketsCount, myTicketsCount]);

  const statusCounts = useMemo(() => {
    const counts = filteredAndSortedTickets.reduce((acc, ticket) => {
      acc[ticket.status] = (acc[ticket.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      all: filteredAndSortedTickets.length,
      open: counts.open || 0,
      in_progress: counts.in_progress || 0,
      in_review: counts.in_review || 0,
      resolved: counts.resolved || 0,
      closed: counts.closed || 0,
    };
  }, [filteredAndSortedTickets]);

  const myTicketStats = useMemo(() => {
    if (activeTab !== 'my') return null;

    const myTickets = currentTickets;
    const reportedByMe = myCreatedTickets?.tickets || [];
    const assignedToMe = myAssignedTickets?.tickets || [];

    return {
      total: myTickets.length,
      reported: reportedByMe.length,
      assigned: assignedToMe.length,
      open: myTickets.filter(t => t.status === 'open').length,
      inProgress: myTickets.filter(t => t.status === 'in_progress').length,
      closed: myTickets.filter(t => t.status === 'closed' || t.status === 'resolved').length,
      urgent: myTickets.filter(t => t.priority === 'critical').length,
      high: myTickets.filter(t => t.priority === 'high').length
    };
  }, [activeTab, currentTickets, myCreatedTickets, myAssignedTickets]);

  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
  };

  const handleFilterChange = (newFilters: {
    searchQuery?: string;
    statusFilter?: string;
    priorityFilter?: string;
  }) => {
    setCurrentPage(1);
    if (newFilters.searchQuery !== undefined) setSearchQuery(newFilters.searchQuery);
    if (newFilters.statusFilter !== undefined) setStatusFilter(newFilters.statusFilter);
    if (newFilters.priorityFilter !== undefined) setPriorityFilter(newFilters.priorityFilter);
  };

  const handleSearchKeyPress = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setDebouncedSearchQuery(searchQuery);
      setCurrentPage(1);
    }
  }, [searchQuery]);

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    setCurrentPage(1);
  };

  const totalPages = Math.ceil((currentData?.total || 0) / pageSize);
  const hasNextPage = currentPage < totalPages;
  const hasPrevPage = currentPage > 1;

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

  const isLoading = activeTab === 'all' ? isLoadingAll : (isLoadingCreated || isLoadingAssigned);

  return (
    <>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          {activeTab === 'my' ? 'My Tickets' : 'Browse Tickets'}
        </h1>
        <p className="mt-2 text-gray-600">
          {activeTab === 'my'
            ? 'View and manage tickets assigned to you or created by you'
            : 'Manage your tickets with AI-powered assistance'
          }
        </p>
      </div>

      <div className="mb-8">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="all" className="flex items-center gap-2">
              <List className="w-4 h-4" />
              All Tickets
              <Badge variant="secondary" className="ml-1">
                {ticketCounts.all}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="my" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              My Tickets
              <Badge variant="secondary" className="ml-1">
                {ticketCounts.my}
              </Badge>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {activeTab === 'my' && myTicketStats && (
        <div className="space-y-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total</CardTitle>
                <User className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{myTicketStats.total}</div>
                <p className="text-xs text-muted-foreground">Your tickets</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Reported</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{myTicketStats.reported}</div>
                <p className="text-xs text-muted-foreground">Tickets you created</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Assigned</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{myTicketStats.assigned}</div>
                <p className="text-xs text-muted-foreground">Tickets assigned to you</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Completed</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{myTicketStats.closed}</div>
                <p className="text-xs text-muted-foreground">Closed tickets</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Priority Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-sm">Critical</span>
                  </div>
                  <Badge variant={myTicketStats.urgent > 0 ? "destructive" : "secondary"}>
                    {myTicketStats.urgent}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className="text-sm">High</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={myTicketStats.high > 0 ? "bg-orange-500 text-white border-orange-500" : "bg-gray-50 text-gray-500 border-gray-200"}
                  >
                    {myTicketStats.high}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Status Overview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Open</span>
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                    {myTicketStats.open}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">In Progress</span>
                  <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                    {myTicketStats.inProgress}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Closed</span>
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    {myTicketStats.closed}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

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
        <Badge variant="outline" className="px-3 py-1 bg-purple-50 text-purple-700 border-purple-200">
          In Review: {statusCounts.in_review}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-green-50 text-green-700 border-green-200">
          Resolved: {statusCounts.resolved}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 bg-green-50 text-green-700 border-green-200">
          Closed: {statusCounts.closed}
        </Badge>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search tickets by title, description, tags..."
            value={searchQuery}
            onChange={(e) => handleFilterChange({ searchQuery: e.target.value })}
            onKeyPress={handleSearchKeyPress}
            className="pl-10 bg-input-background"
          />
        </div>

        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={(value) => handleFilterChange({ statusFilter: value })}>
            <SelectTrigger className="w-[140px] bg-input-background">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
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

          <Select value={priorityFilter} onValueChange={(value) => handleFilterChange({ priorityFilter: value })}>
            <SelectTrigger className="w-[140px] bg-input-background">
              <SelectValue />
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
            <SelectTrigger className="w-[120px] bg-input-background">
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

      <div className="text-sm text-muted-foreground mb-6">
        Showing {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, currentData?.total || 0)} of {currentData?.total || 0} tickets
      </div>

      <div className="space-y-4">
        {filteredAndSortedTickets.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg mb-2">{isLoading ? 'Loading tickets...' : 'No tickets found'}</h3>
            <p className="text-muted-foreground">
              {isLoading ? 'Please wait while we fetch your tickets' :
               (searchQuery || statusFilter !== "all" || priorityFilter !== "all"
                ? "Try adjusting your search or filters"
                : "Create your first ticket to get started")}
            </p>
          </div>
        ) : (
          filteredAndSortedTickets.map((ticket) => (
            <Card
              key={ticket.id}
              className="shadow-md hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => window.open(`/tickets/${ticket.id}`, '_self')}
            >
              <CardContent className="p-4">
                {/* Header - Title, Priority, Status, and ID */}
                <div className="mb-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 flex-1 pr-4">
                      {ticket.title}
                    </h3>
                    <span className="text-sm text-gray-500 font-mono whitespace-nowrap">
                      #{ticket.id}
                    </span>
                  </div>

                  {/* Priority and Status row */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${getPriorityColor(ticket.priority)}`}></div>
                      <span className="text-sm capitalize font-medium">{formatPriority(ticket.priority)}</span>
                    </div>
                    <Badge variant="secondary" className={getStatusColor(ticket.status)}>
                      {formatStatus(ticket.status)}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-4">
                  <p className="text-gray-600 line-clamp-2 leading-relaxed">
                    {ticket.description}
                  </p>

                  {ticket.tags && ticket.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {ticket.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          <Tag className="w-3 h-3 mr-1" />
                          {tag}
                        </Badge>
                      ))}
                      {ticket.tags.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{ticket.tags.length - 3} more
                        </Badge>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-500 pt-4 mt-4 border-t border-gray-100 bg-gray-50/50 -mx-4 px-4 pb-4">
                  <div className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    <TicketCreator ticket={ticket} showAvatar={false} />
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    <span>{ticket.team_name}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-8">
          <div className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={!hasPrevPage}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>

            <div className="flex items-center gap-1">
              {(() => {
                const pages = [];

                if (totalPages <= 7) {
                  for (let i = 1; i <= totalPages; i++) {
                    pages.push(
                      <Button
                        key={i}
                        variant={currentPage === i ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(i)}
                        className="w-8 h-8 p-0"
                      >
                        {i}
                      </Button>
                    );
                  }
                } else {
                  pages.push(
                    <Button
                      key={1}
                      variant={currentPage === 1 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(1)}
                      className="w-8 h-8 p-0"
                    >
                      1
                    </Button>
                  );

                  if (currentPage > 4) {
                    pages.push(
                      <span key="ellipsis1" className="px-2 text-gray-400">
                        ...
                      </span>
                    );
                  }

                  const start = Math.max(2, currentPage - 1);
                  const end = Math.min(totalPages - 1, currentPage + 1);

                  for (let i = start; i <= end; i++) {
                    pages.push(
                      <Button
                        key={i}
                        variant={currentPage === i ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(i)}
                        className="w-8 h-8 p-0"
                      >
                        {i}
                      </Button>
                    );
                  }

                  if (currentPage < totalPages - 3) {
                    pages.push(
                      <span key="ellipsis2" className="px-2 text-gray-400">
                        ...
                      </span>
                    );
                  }

                  pages.push(
                    <Button
                      key={totalPages}
                      variant={currentPage === totalPages ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(totalPages)}
                      className="w-8 h-8 p-0"
                    >
                      {totalPages}
                    </Button>
                  );
                }

                return pages;
              })()}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={!hasNextPage}
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
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