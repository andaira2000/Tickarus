#!/usr/bin/env python3
"""
Enhanced repository setup script for realistic dissertation demo
Adds commit history, issues, PRs, and realistic content to GitHub repositories
"""

import asyncio
import json
import os
import sys
import tempfile
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from github import Github

# GitHub client setup
GITHUB_TOKEN = settings.github_token
ORG_NAME = settings.github_org_name
github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here" else None

# Fake contributors for realistic commit history
CONTRIBUTORS = [
    {"name": "Sarah Chen", "email": "sarah.chen@company.com"},
    {"name": "Marcus Rodriguez", "email": "marcus.r@company.com"},
    {"name": "Priya Patel", "email": "priya.patel@company.com"},
    {"name": "David Kim", "email": "david.kim@company.com"},
    {"name": "Emma Thompson", "email": "emma.t@company.com"},
    {"name": "Ahmed Hassan", "email": "ahmed.hassan@company.com"},
]

# Enhanced repository content with realistic features
ENHANCED_REPOS = {
    "frontend-webapp": {
        "language": "TypeScript",
        "description": "Customer portal web application built with React and TypeScript",
        "topics": ["react", "typescript", "customer-portal", "web-app", "frontend"],
        "enhanced_files": {
            "src/components/LoginForm.tsx": '''import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { validateEmail } from '../utils/validation';
import './LoginForm.css';

interface LoginFormProps {
  onSuccess: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      onSuccess();
    } catch (err) {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <div className="form-group">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      {error && <div className="error-message">{error}</div>}
      <button type="submit" disabled={loading}>
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  );
};''',
            "src/hooks/useAuth.ts": '''import { useState, useCallback } from 'react';
import { authService } from '../services/authService';
import { User } from '../types/User';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const userData = await authService.login(email, password);
      setUser(userData);
      localStorage.setItem('authToken', userData.token);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('authToken');
  }, []);

  return { user, login, logout, loading };
};''',
            "src/services/authService.ts": '''import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const authService = {
  async login(email: string, password: string) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        throw new Error('Invalid credentials');
      }
      throw new Error('Login failed. Please try again.');
    }
  }
};''',
            "src/utils/validation.ts": '''export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password: string): boolean => {
  return password.length >= 8;
};''',
            "src/components/LoginForm.css": '''.login-form {
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}

.error-message {
  color: #d32f2f;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

button[type="submit"] {
  width: 100%;
  padding: 0.75rem;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}

button[type="submit"]:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}''',
            "src/types/User.ts": '''export interface User {
  id: string;
  email: string;
  name: string;
  token: string;
  role: 'admin' | 'user';
  createdAt: string;
}''',
            "tests/LoginForm.test.tsx": '''import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginForm } from '../src/components/LoginForm';
import { useAuth } from '../src/hooks/useAuth';

jest.mock('../src/hooks/useAuth');

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('LoginForm', () => {
  const mockLogin = jest.fn();
  const mockOnSuccess = jest.fn();

  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      logout: jest.fn(),
      user: null,
      loading: false
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders login form', () => {
    render(<LoginForm onSuccess={mockOnSuccess} />);
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows error for invalid email', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('calls login function with correct credentials', async () => {
    render(<LoginForm onSuccess={mockOnSuccess} />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });
});''',
            "CONTRIBUTING.md": '''# Contributing to Frontend WebApp

## Development Setup

1. Clone the repository
2. Install dependencies: `npm install`
3. Start development server: `npm start`
4. Run tests: `npm test`

## Code Style

- Use TypeScript for all new code
- Follow ESLint configuration
- Write tests for new components
- Use conventional commit messages

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add/update tests
4. Ensure all tests pass
5. Submit pull request with detailed description

## Bug Reports

Please include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Browser/environment details
''',
        },
        "issues": [
            {
                "title": "Authentication timeout occurs after 30 seconds on production",
                "body": """## Bug Report

**Environment:** Production
**Browser:** Chrome 120.0, Safari 17.1
**Affected Users:** ~15% of login attempts

### Description
Users are experiencing authentication timeouts when trying to log in. The login form submits successfully but times out after exactly 30 seconds with a network error.

### Steps to Reproduce
1. Go to login page
2. Enter valid credentials
3. Click "Sign In"
4. Wait 30+ seconds
5. Observe timeout error

### Expected Behavior
Login should complete within 5-10 seconds

### Actual Behavior
Request times out after 30 seconds with error: `NetworkError: Timeout`

### Error Logs
```
POST /api/auth/login - 504 Gateway Timeout
Response time: 30001ms
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
```

### Additional Context
- Issue started appearing after deployment v2.3.1 
- Backend logs show successful auth but delayed response
- Load balancer timeout might be set to 30s
- Affects both new and existing users

**Priority:** High - blocking user access
**Labels:** bug, authentication, production, timeout
""",
                "labels": ["bug", "high-priority", "authentication", "production"]
            },
            {
                "title": "Implement dark mode theme support",
                "body": """## Feature Request

### Description
Add dark mode support to improve user experience, especially for users working in low-light environments.

### Acceptance Criteria
- [ ] Toggle switch in user settings
- [ ] Dark theme for all components
- [ ] Persist user preference in localStorage
- [ ] System theme detection (prefers-color-scheme)
- [ ] Smooth transitions between themes

### Design Mockups
Available in Figma: [Dark Mode Designs](https://figma.com/darkmode)

### Technical Notes
- Use CSS custom properties for theme variables
- Consider contrast ratios for accessibility (WCAG AA)
- Test with all existing components

**Priority:** Medium
**Labels:** enhancement, ui-ux, accessibility
""",
                "labels": ["enhancement", "ui-ux", "accessibility"]
            },
            {
                "title": "Memory leak in user dashboard component",
                "body": """## Bug Report

**Environment:** Development, Staging
**Component:** UserDashboard.tsx
**Memory Impact:** ~50MB per session

### Description
The UserDashboard component appears to have a memory leak that grows over time, especially when users navigate between different sections.

### Investigation Results
- Memory usage increases by ~2-3MB every time dashboard re-renders
- Event listeners not being cleaned up properly
- Possible issue with websocket connections not closing

### Proposed Solution
1. Audit useEffect cleanup functions
2. Check websocket connection lifecycle
3. Review event listener management
4. Add memory profiling to CI pipeline

### Performance Impact
- Browser becomes sluggish after ~20 minutes of use
- Especially affects users with multiple tabs open
- Mobile devices more severely impacted

**Priority:** Medium
**Labels:** bug, performance, memory-leak
""",
                "labels": ["bug", "performance", "memory-leak"]
            }
        ]
    },
    
    "backend-api": {
        "language": "Python",
        "description": "FastAPI backend service handling authentication, ticket management, and team operations",
        "topics": ["fastapi", "python", "api", "backend", "postgresql"],
        "enhanced_files": {
            "app/services/auth_service.py": '''from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import settings
from ..models.user import User, UserCreate
from ..db.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Create new user account"""
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user''',
            "app/models/ticket.py": '''from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    BLOCKED = "blocked"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketBase(BaseModel):
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: Priority = Priority.MEDIUM
    assignee_id: Optional[UUID] = None
    team_id: UUID

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    assignee_id: Optional[UUID] = None

class Ticket(TicketBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    
    class Config:
        from_attributes = True''',
            "app/core/database_connection.py": '''import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError

from ..config import settings

logger = logging.getLogger(__name__)

# Database connection configuration
SQLALCHEMY_DATABASE_URL = settings.database_url

# Connection pool configuration for production
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance"""
    if "sqlite" in SQLALCHEMY_DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

@contextmanager
def get_db_connection():
    """Get database connection with proper error handling"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except DisconnectionError:
        logger.error("Database disconnection error")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def check_db_health():
    """Check database connectivity"""
    try:
        with get_db_connection() as db:
            db.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False''',
            "tests/test_auth_service.py": '''import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import jwt

from app.services.auth_service import AuthService
from app.models.user import User, UserCreate

class TestAuthService:
    def setup_method(self):
        self.auth_service = AuthService()

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = self.auth_service.get_password_hash(password)
        
        assert hashed != password
        assert self.auth_service.verify_password(password, hashed)
        assert not self.auth_service.verify_password("wrong_password", hashed)

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = self.auth_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = self.auth_service.verify_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["user_id"] == "123"
        assert "exp" in payload

    def test_token_expiration(self):
        """Test token expiration"""
        # Create token that expires immediately
        self.auth_service.access_token_expire_minutes = 0
        data = {"sub": "user@example.com"}
        token = self.auth_service.create_access_token(data)
        
        # Wait a moment and verify token is expired
        import time
        time.sleep(1)
        
        payload = self.auth_service.verify_token(token)
        assert payload is None

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = self.auth_service.get_password_hash("password123")
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = self.auth_service.authenticate_user(mock_db, "test@example.com", "password123")
        assert result == mock_user

    def test_authenticate_user_invalid_password(self):
        """Test authentication with invalid password"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = self.auth_service.get_password_hash("password123")
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = self.auth_service.authenticate_user(mock_db, "test@example.com", "wrong_password")
        assert result is None

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.auth_service.authenticate_user(mock_db, "nonexistent@example.com", "password123")
        assert result is None''',
            "app/utils/error_handlers.py": '''import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DatabaseError, IntegrityError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database connection and query errors"""
    logger.error(f"Database error on {request.url}: {str(exc)}")
    
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=409,
            content={
                "error": "Constraint violation",
                "detail": "The operation violates a database constraint",
                "type": "integrity_error"
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error",
            "detail": "An error occurred while processing your request",
            "type": "database_error"
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error on {request.url}: {str(exc)}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
            "type": "validation_error"
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with enhanced logging"""
    logger.warning(f"HTTP {exc.status_code} on {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "type": "http_error",
            "status_code": exc.status_code
        }
    )''',
        },
        "issues": [
            {
                "title": "Database connection pool exhausted during peak traffic",
                "body": """## Production Issue

**Severity:** Critical
**Environment:** Production
**Time:** 2024-01-15 14:30 UTC
**Duration:** ~15 minutes
**Affected Users:** All users

### Description
The application became unresponsive during peak traffic hours. Database connection pool was exhausted, causing 500 errors for all API requests.

### Error Messages
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 30 reached, connection timed out
FastAPI 500 Internal Server Error
```

### Timeline
- 14:30 - First alerts triggered
- 14:32 - All API endpoints returning 500s
- 14:35 - Database connection pool at 100% utilization
- 14:45 - Service restarted, connections restored
- 14:47 - Service fully operational

### Root Cause Analysis
1. Traffic spike (3x normal load) due to marketing campaign
2. Long-running queries not releasing connections properly
3. Connection pool size insufficient for load
4. Missing connection timeout configuration

### Immediate Actions Taken
- Restarted application servers
- Increased connection pool size from 20 to 50
- Added connection monitoring alerts

### Long-term Solutions Needed
- [ ] Implement connection pool monitoring
- [ ] Add query timeout enforcement
- [ ] Review and optimize slow queries
- [ ] Load testing with realistic traffic patterns
- [ ] Circuit breaker pattern for database calls

**Labels:** critical, database, performance, production-incident
""",
                "labels": ["critical", "database", "performance", "production-incident"]
            },
            {
                "title": "JWT token expiration not handled gracefully in client",
                "body": """## Bug Report

**Component:** Authentication API
**Impact:** Medium - affects user experience

### Description
When JWT tokens expire, the API returns 401 Unauthorized, but the frontend doesn't handle this gracefully, causing users to see generic error messages instead of being redirected to login.

### Current Behavior
1. User makes API request with expired token
2. API returns `{"detail": "Token has expired"}`
3. Frontend shows "Request failed" error
4. User remains on current page, confused

### Expected Behavior
1. API returns structured error with token expiration info
2. Frontend detects token expiration
3. User is redirected to login page
4. After login, user returns to previous page

### Technical Details
```python
# Current API response
{"detail": "Token has expired"}

# Proposed API response
{
  "error": "authentication_failed",
  "detail": "Token has expired", 
  "error_code": "TOKEN_EXPIRED",
  "expires_at": "2024-01-15T10:30:00Z"
}
```

### Proposed Solution
1. Enhance JWT error responses with structured data
2. Add token refresh endpoint
3. Implement automatic token refresh on frontend
4. Add token expiration warnings (5 min before expiry)

**Priority:** Medium
**Labels:** authentication, user-experience, api
""",
                "labels": ["authentication", "user-experience", "api"]
            }
        ]
    }
}

def git_command(repo_path: Path, command: List[str], author: Dict[str, str] = None):
    """Run git command with optional author override"""
    env = os.environ.copy()
    if author:
        env['GIT_AUTHOR_NAME'] = author['name']
        env['GIT_AUTHOR_EMAIL'] = author['email']
        env['GIT_COMMITTER_NAME'] = author['name']
        env['GIT_COMMITTER_EMAIL'] = author['email']
    
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return None

async def enhance_repository(repo_name: str, repo_data: Dict):
    """Enhance a single repository with realistic content"""
    print(f"Enhancing repository: {repo_name}")
    
    if not github_client:
        print("GitHub client not available - skipping GitHub integration")
        return
    
    try:
        repo = github_client.get_repo(f"{ORG_NAME}/{repo_name}")
        
        # Create a temporary directory for enhancements
        temp_dir = Path(tempfile.mkdtemp(prefix=f"enhance_{repo_name}_"))
        
        # Clone the repository
        git_command(temp_dir, ["clone", f"https://github.com/{ORG_NAME}/{repo_name}.git", "."]) 
        
        # Add enhanced files
        for file_path, content in repo_data["enhanced_files"].items():
            full_path = temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Create realistic commit history with multiple contributors
        await create_realistic_commit_history(temp_dir, repo_name)
        
        # Push changes
        git_command(temp_dir, ["push", "origin", "main"])
        
        # Create GitHub issues
        for issue_data in repo_data.get("issues", []):
            await create_github_issue(repo, issue_data)
        
        # Add repository topics
        if repo_data.get("topics"):
            repo.replace_topics(repo_data["topics"])
        
        print(f"Enhanced {repo_name} successfully")
        
    except Exception as e:
        print(f"Error enhancing {repo_name}: {e}")

async def create_realistic_commit_history(repo_path: Path, repo_name: str):
    """Create realistic commit history with multiple contributors"""
    
    # Define realistic commit scenarios
    commit_scenarios = [
        {"type": "feat", "message": "Add user authentication system", "files": ["src/auth/", "tests/auth/"]},
        {"type": "fix", "message": "Fix memory leak in connection pool", "files": ["src/database/"]},
        {"type": "perf", "message": "Optimize database query performance", "files": ["src/services/"]},
        {"type": "docs", "message": "Update API documentation", "files": ["docs/", "README.md"]},
        {"type": "test", "message": "Add integration tests for auth flow", "files": ["tests/integration/"]},
        {"type": "refactor", "message": "Restructure error handling", "files": ["src/utils/", "src/errors/"]},
        {"type": "feat", "message": "Implement rate limiting middleware", "files": ["src/middleware/"]},
        {"type": "fix", "message": "Handle edge case in password validation", "files": ["src/auth/validation.py"]},
        {"type": "chore", "message": "Update dependencies and security patches", "files": ["requirements.txt", "package.json"]},
        {"type": "feat", "message": "Add comprehensive logging system", "files": ["src/logging/", "config/logging.yml"]},
    ]
    
    # Create commits over the past 6 months
    start_date = datetime.now() - timedelta(days=180)
    
    for i, scenario in enumerate(commit_scenarios):
        # Random contributor
        author = random.choice(CONTRIBUTORS)
        
        # Random date in the past 6 months
        days_ago = random.randint(1, 180)
        commit_date = start_date + timedelta(days=days_ago)
        
        # Create some file changes
        for file_path in scenario["files"]:
            if "/" in file_path:  # Directory
                dir_path = repo_path / file_path
                dir_path.mkdir(parents=True, exist_ok=True)
                (dir_path / f"module_{i}.py").write_text(f"# {scenario['message']}\\nprint('Module updated')\\n")
            else:  # Single file
                file_full_path = repo_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_full_path, 'a') as f:
                    f.write(f"\\n# {scenario['message']} - {commit_date.strftime('%Y-%m-%d')}\\n")
        
        # Stage and commit changes
        git_command(repo_path, ["add", "."], author=author)
        git_command(repo_path, [
            "commit", 
            "-m", f"{scenario['type']}: {scenario['message']}",
            "--date", commit_date.strftime("%Y-%m-%d %H:%M:%S")
        ], author=author)

async def create_github_issue(repo, issue_data: Dict):
    """Create a realistic GitHub issue"""
    try:
        issue = repo.create_issue(
            title=issue_data["title"],
            body=issue_data["body"],
            labels=issue_data.get("labels", [])
        )
        print(f"  Created issue: {issue_data['title']}")
    except Exception as e:
        print(f"  Failed to create issue: {e}")

async def enhance_all_repositories():
    """Enhance all repositories with realistic content"""
    print("Enhancing repositories with realistic content...")
    print("=" * 60)
    
    if not github_client:
        print("❌ GitHub token not configured properly")
        print("Please ensure GITHUB_TOKEN is set in your .env file")
        return
    
    for repo_name, repo_data in ENHANCED_REPOS.items():
        await enhance_repository(repo_name, repo_data)
        print()
    
    print("Repository enhancement complete!")
    print()
    print("Enhanced features:")
    print("- Realistic commit history (6 months, multiple contributors)")
    print("- Detailed GitHub issues with proper labels")
    print("- Enhanced file structure with actual code")
    print("- Repository topics and metadata")
    print("- Tests and documentation")

if __name__ == "__main__":
    asyncio.run(enhance_all_repositories())