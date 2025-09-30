'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  List,
  Users,
  Search,
  Settings,
  LogOut,
  Plus,
  Bell,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/lib/store/auth';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: ReactNode;
}

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Tickets',
    href: '/tickets',
    icon: List,
  },
  {
    name: 'Teams',
    href: '/teams',
    icon: Users,
  },
];

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isInitialized, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('sidebar-open');
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  const isPathActive = (href: string) => {
    if (pathname === href) return true;

    if (href === '/tickets' && pathname === '/tickets/my') return false;
    if (href === '/tickets/my' && pathname === '/tickets') return false;

    if (href !== '/tickets' && pathname.startsWith(href + '/')) return true;
    
    return false;
  };

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isInitialized, router]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const toggleSidebar = () => {
    const newState = !sidebarOpen;
    setSidebarOpen(newState);
    if (typeof window !== 'undefined') {
      localStorage.setItem('sidebar-open', JSON.stringify(newState));
    }
  };

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className={`fixed inset-y-0 z-50 flex ${sidebarOpen ? 'w-64' : 'w-16'} flex-col transition-all duration-300 ease-in-out`}>
        <div className={`flex grow flex-col gap-y-5 overflow-y-auto bg-white py-4 shadow-sm ${sidebarOpen ? 'px-6' : 'px-2'} transition-all duration-300`}>
          <div className={`flex h-16 shrink-0 items-center ${sidebarOpen ? 'justify-between' : 'justify-center'}`}>
            {sidebarOpen && (
              <h1 className="text-2xl font-bold text-teal-600 text-center">Tickarus</h1>
            )}
            <Button
              variant="ghost"
              onClick={toggleSidebar}
              className={`hover:bg-gray-100 rounded-md p-2 ${sidebarOpen ? '' : 'w-12 h-12'}`}
            >
              {sidebarOpen ? <ChevronLeft className="h-6 w-6" /> : <ChevronRight className="h-6 w-6" />}
            </Button>
          </div>

          <Link href="/tickets/new">
            <Button className={`w-full ${sidebarOpen ? 'justify-start gap-x-3' : 'justify-center'} p-2 text-sm leading-6 font-semibold`}>
              <Plus className="h-6 w-6 shrink-0" />
              {sidebarOpen && 'New Ticket'}
            </Button>
          </Link>

          <nav className="flex flex-1 flex-col">
            <ul role="list" className="flex flex-1 flex-col gap-y-7">
              <li>
                <ul role="list" className="-mx-2 space-y-1">
                  {navigation.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className={cn(
                          isPathActive(item.href)
                            ? 'bg-gray-100 text-gray-900'
                            : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50',
                          'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold transition-colors duration-200',
                          !sidebarOpen && 'justify-center'
                        )}
                        title={!sidebarOpen ? item.name : undefined}
                      >
                        <item.icon
                          className={cn(
                            isPathActive(item.href)
                              ? 'text-gray-900'
                              : 'text-gray-400 group-hover:text-gray-900',
                            'h-6 w-6 shrink-0 transition-colors duration-200'
                          )}
                          aria-hidden="true"
                        />
                        {sidebarOpen && item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            </ul>
          </nav>

          <div className="mt-auto">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className={`w-full ${sidebarOpen ? 'justify-start' : 'justify-center'} p-2 hover:bg-gray-50 transition-colors duration-200`}>
                  <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-medium">
                      {(user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U').toUpperCase()}
                    </span>
                  </div>
                  {sidebarOpen && (
                    <div className="ml-3 text-left">
                      <p className="text-sm font-medium text-gray-900">
                        {user?.full_name || user?.email}
                      </p>
                      <p className="text-xs text-gray-500">{user?.email}</p>
                    </div>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div className={`${sidebarOpen ? 'pl-64' : 'pl-16'} transition-all duration-300 ease-in-out`}>
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex flex-1"></div>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              <Button variant="ghost" size="sm">
                <Bell className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>

        <main className="py-8">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}