# Tickarus Frontend

A modern, sleek React/TypeScript/Next.js frontend for the Tickarus ticket management system.

## Features

### ✅ Implemented
- **Authentication**: Login/Register with JWT token handling
- **Dashboard**: Overview with stats and recent tickets
- **Ticket Management**: List view with advanced filtering and search
- **My Tickets**: Personal ticket views (created, assigned, commented)
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- **State Management**: Zustand for auth state, React Query for data fetching
- **Responsive Design**: Mobile-first approach with clean, professional styling

### 🚧 Coming Next
- Ticket detail view with comments system
- Create/edit ticket functionality
- Team management pages
- Real-time notifications
- AI-powered features (as per dissertation requirements)

## Tech Stack

- **Framework**: Next.js 13+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: Zustand (auth) + React Query (API data)
- **Forms**: React Hook Form + Zod validation
- **Icons**: Lucide React
- **Notifications**: Sonner

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running backend API (see ../backend/README.md)

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables:
   ```bash
   # Update .env.local with your backend API URL
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000)

## Available Pages

### Public Routes
- `/` - Home page (redirects based on auth status)
- `/login` - User login
- `/register` - User registration

### Protected Routes (require authentication)
- `/dashboard` - Main dashboard with stats and recent tickets
- `/tickets` - All tickets list with advanced filtering
- `/tickets/my` - Personal tickets (created, assigned, commented)

## Key Features

### Authentication Flow
- JWT token storage in localStorage
- Automatic token refresh handling
- Route protection with auth store
- Persistent login state

### Ticket Filtering
- Filter by team, status, priority, assignee
- Full-text search across ticket content
- Pagination support
- Real-time filter updates

### Modern UI Components
- Consistent design system with shadcn/ui
- Responsive layouts for all screen sizes
- Loading states and error handling
- Toast notifications for user feedback

## Integration with Backend

Ensure the backend is running on `http://localhost:8000` (or update `NEXT_PUBLIC_API_URL` in `.env.local`).

The frontend expects these main endpoints:
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `GET /api/tickets` - List tickets with filters
- `GET /api/teams` - List user teams

Make sure CORS is properly configured in the backend to allow frontend origins.
