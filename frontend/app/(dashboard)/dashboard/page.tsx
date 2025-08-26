'use client';

import { useQuery } from '@tanstack/react-query';
import { Ticket, Users, Clock, CheckCircle } from 'lucide-react';

import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { TicketPriority, TicketStatus } from '@/lib/types';
import { useAuthStore } from '@/lib/store/auth';

function DashboardContent() {
  const { user } = useAuthStore();
  
  const { data: tickets } = useQuery({
    queryKey: ['tickets', { page: 1, page_size: 5 }],
    queryFn: () => apiClient.getTickets({ page: 1, page_size: 5 }),
  });

  const { data: myTickets } = useQuery({
    queryKey: ['my-tickets', user?.id],
    queryFn: () => apiClient.getTickets({ 
      created_by: user!.id,
      page: 1, 
      page_size: 5 
    }),
    enabled: !!user?.id,
  });

  const { data: teams } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.getTeams(),
  });

  const stats = [
    {
      name: 'Total Tickets',
      value: tickets?.total || 0,
      icon: Ticket,
      change: '+12%',
      changeType: 'positive',
    },
    {
      name: 'My Tickets',
      value: myTickets?.total || 0,
      icon: Clock,
      change: '+3%',
      changeType: 'positive',
    },
    {
      name: 'Teams',
      value: teams?.length || 0,
      icon: Users,
      change: '0%',
      changeType: 'neutral',
    },
    {
      name: 'Resolved Today',
      value: 12, // This would come from analytics
      icon: CheckCircle,
      change: '+25%',
      changeType: 'positive',
    },
  ];

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

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome back! Here&apos;s what&apos;s happening with your tickets.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.name}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className={`text-xs ${
                stat.changeType === 'positive' 
                  ? 'text-green-600' 
                  : stat.changeType === 'negative'
                  ? 'text-red-600'
                  : 'text-gray-500'
              }`}>
                {stat.change} from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Tickets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Tickets</CardTitle>
            <CardDescription>Latest tickets across all teams</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tickets?.tickets?.map((ticket) => (
                <div key={ticket.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {ticket.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {ticket.team_name} • {new Date(ticket.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant={getPriorityColor(ticket.priority)}>
                      {ticket.priority}
                    </Badge>
                    <Badge variant={getStatusColor(ticket.status)}>
                      {ticket.status}
                    </Badge>
                  </div>
                </div>
              ))}
              {(!tickets?.tickets || tickets.tickets.length === 0) && (
                <p className="text-sm text-gray-500 text-center py-4">
                  No tickets yet. Create your first ticket to get started!
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>My Teams</CardTitle>
            <CardDescription>Teams you&apos;re a member of</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {teams?.map((team) => (
                <div key={team.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {team.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {team.members_count} members
                    </p>
                  </div>
                  <div className="flex items-center">
                    <Users className="h-4 w-4 text-gray-400" />
                  </div>
                </div>
              ))}
              {(!teams || teams.length === 0) && (
                <p className="text-sm text-gray-500 text-center py-4">
                  You&apos;re not part of any teams yet.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

export default function DashboardPage() {
  return (
    <DashboardLayout>
      <DashboardContent />
    </DashboardLayout>
  );
}