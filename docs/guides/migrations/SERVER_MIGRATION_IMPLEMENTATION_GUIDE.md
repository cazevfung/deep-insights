# Server Migration Implementation Guide

## Overview

This guide provides implementation details, code examples, and patterns for migrating the Research Tool to a cloud-hosted, multi-user platform. For the complete migration plan, see [SERVER_MIGRATION_PLAN.md](./SERVER_MIGRATION_PLAN.md).

## Table of Contents

1. [Database Setup](#database-setup)
2. [Authentication Implementation](#authentication-implementation)
3. [Authorization Implementation](#authorization-implementation)
4. [Data Migration](#data-migration)
5. [Report Sharing Implementation](#report-sharing-implementation)
6. [API Implementation](#api-implementation)
7. [Frontend Implementation](#frontend-implementation)
8. [Deployment Configuration](#deployment-configuration)

---

## Database Setup

### PostgreSQL Configuration

#### 1. Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql
brew services start postgresql
```

#### 2. Create Database
```sql
CREATE DATABASE research_tool;
CREATE USER research_tool_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE research_tool TO research_tool_user;
```

#### 3. Install Alembic for Migrations
```bash
pip install alembic sqlalchemy
```

#### 4. Initialize Alembic
```bash
cd backend
alembic init alembic
```

#### 5. Configure Alembic (alembic.ini)
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://research_tool_user:secure_password@localhost/research_tool
```

#### 6. Create Initial Migration
```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.Text()),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('email_verification_token', sa.String(255)),
        sa.Column('password_reset_token', sa.String(255)),
        sa.Column('password_reset_expires_at', sa.Timestamp()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('last_login_at', sa.Timestamp()),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(100), unique=True, nullable=False),
        sa.Column('batch_id', sa.String(100), unique=True, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='initialized'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('scratchpad', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('phase_artifacts', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('step_digests', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('completed_at', sa.Timestamp()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_session_id', 'sessions', ['session_id'])
    op.create_index('idx_sessions_batch_id', 'sessions', ['batch_id'])
    
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('published_at', sa.Timestamp()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', 'version'),
    )
    op.create_index('idx_reports_user_id', 'reports', ['user_id'])
    op.create_index('idx_reports_session_id', 'reports', ['session_id'])
    
    # Create report_shares table
    op.create_table(
        'report_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_token', sa.String(255), unique=True, nullable=False),
        sa.Column('share_type', sa.String(50), nullable=False, server_default='public'),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('expires_at', sa.Timestamp()),
        sa.Column('max_views', sa.Integer()),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('allow_download', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_export', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.Timestamp(), server_default=sa.func.current_timestamp()),
        sa.Column('last_accessed_at', sa.Timestamp()),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_report_shares_share_token', 'report_shares', ['share_token'])

def downgrade():
    op.drop_table('report_shares')
    op.drop_table('reports')
    op.drop_table('sessions')
    op.drop_table('users')
```

#### 7. Run Migration
```bash
alembic upgrade head
```

### Redis Configuration

#### 1. Install Redis
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS (Homebrew)
brew install redis
brew services start redis
```

#### 2. Configure Redis
```conf
# redis.conf
bind 127.0.0.1
port 6379
maxmemory 256mb
maxmemory-policy allkeys-lru
```

#### 3. Install Redis Python Client
```bash
pip install redis
```

---

## Authentication Implementation

### Backend Authentication

#### 1. Install Dependencies
```bash
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

#### 2. Create Authentication Module (backend/app/auth/__init__.py)
```python
"""Authentication module."""
from .jwt import create_access_token, verify_token
from .password import hash_password, verify_password
from .dependencies import get_current_user, get_current_active_user

__all__ = [
    'create_access_token',
    'verify_token',
    'hash_password',
    'verify_password',
    'get_current_user',
    'get_current_active_user',
]
```

#### 3. JWT Token Management (backend/app/auth/jwt.py)
```python
"""JWT token management."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status

SECRET_KEY = "your-secret-key-here"  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access"):
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

#### 4. Password Hashing (backend/app/auth/password.py)
```python
"""Password hashing and verification."""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

#### 5. Authentication Dependencies (backend/app/auth/dependencies.py)
```python
"""Authentication dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth.jwt import verify_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user
```

#### 6. Authentication Routes (backend/app/routes/auth.py)
```python
"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.database import get_db
from app.models import User, UserSession
from app.auth.jwt import create_access_token, create_refresh_token, verify_token
from app.auth.password import hash_password, verify_password
from app.auth.dependencies import get_current_user

router = APIRouter()
security = HTTPBearer()

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register new user."""
    # Check if user already exists
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    user = User(
        email=request.email,
        username=request.username,
        password_hash=hash_password(request.password),
        full_name=request.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "User created successfully", "user_id": str(user.id)}

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login user."""
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token in database
    user_session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(user_session)
    
    # Update user last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Use HTTPS in production
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: Session = Depends(get_db)
):
    """Refresh access token."""
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    user_id = payload.get("sub")
    
    # Check if refresh token exists in database
    user_session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Update last used timestamp
    user_session.last_used_at = datetime.utcnow()
    db.commit()
    
    # Create new access token
    access_token = create_access_token(data={"sub": user_id})
    
    return TokenResponse(access_token=access_token)

@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user."""
    # Delete refresh token from database
    db.query(UserSession).filter(UserSession.user_id == current_user.id).delete()
    db.commit()
    
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token")
    
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "email_verified": current_user.email_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }
```

---

## Authorization Implementation

### User Isolation

#### 1. Update Session Routes (backend/app/routes/session.py)
```python
"""Session routes with user isolation."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Session, User
from app.auth.dependencies import get_current_active_user

router = APIRouter()

@router.post("/create")
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new session (user-owned)."""
    session = Session(
        user_id=current_user.id,
        session_id=generate_session_id(),
        batch_id=generate_batch_id(),
        status="initialized",
        metadata={"user_guidance": request.user_guidance}
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.session_id}

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get session (user-owned only)."""
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id  # User isolation
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session
```

#### 2. Update Report Routes (backend/app/routes/reports.py)
```python
"""Report routes with user isolation."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report, User
from app.auth.dependencies import get_current_active_user

router = APIRouter()

@router.get("/{batch_id}")
async def get_report(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get report (user-owned only)."""
    report = db.query(Report).filter(
        Report.batch_id == batch_id,
        Report.user_id == current_user.id  # User isolation
    ).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return report
```

---

## Report Sharing Implementation

### Share Token Generation
```python
"""Share token generation."""
import secrets

def generate_share_token() -> str:
    """Generate secure, URL-safe share token."""
    return secrets.token_urlsafe(32)[:43]  # Limit to 43 characters
```

### Share Routes (backend/app/routes/shares.py)
```python
"""Report sharing routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Report, ReportShare, User
from app.auth.dependencies import get_current_active_user
from app.auth.share_token import generate_share_token
from app.auth.password import hash_password, verify_password

router = APIRouter()

class CreateShareRequest(BaseModel):
    report_id: str
    share_type: str = "public"  # public, unlisted, private
    password: str = None
    expires_at: datetime = None
    max_views: int = None
    allow_download: bool = True
    allow_export: bool = True

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_share(
    request: CreateShareRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create share for report."""
    # Verify report ownership
    report = db.query(Report).filter(
        Report.id == request.report_id,
        Report.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Generate share token
    share_token = generate_share_token()
    
    # Create share
    share = ReportShare(
        report_id=report.id,
        user_id=current_user.id,
        share_token=share_token,
        share_type=request.share_type,
        password_hash=hash_password(request.password) if request.password else None,
        expires_at=request.expires_at,
        max_views=request.max_views,
        allow_download=request.allow_download,
        allow_export=request.allow_export
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    
    return {
        "share_id": str(share.id),
        "share_token": share.share_token,
        "share_url": f"https://example.com/share/{share.share_token}",
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "created_at": share.created_at.isoformat()
    }

@router.get("/{share_token}")
async def get_share(
    share_token: str,
    password: str = None,
    db: Session = Depends(get_db)
):
    """Get share (public access)."""
    # Find share
    share = db.query(ReportShare).filter(
        ReportShare.share_token == share_token
    ).first()
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    
    # Check if share is expired
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share has expired"
        )
    
    # Check if max views exceeded
    if share.max_views and share.view_count >= share.max_views:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share has reached maximum views"
        )
    
    # Check password if required
    if share.share_type == "private" and share.password_hash:
        if not password or not verify_password(password, share.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required"
            )
    
    # Increment view count
    share.view_count += 1
    share.last_accessed_at = datetime.utcnow()
    db.commit()
    
    # Get report
    report = db.query(Report).filter(Report.id == share.report_id).first()
    
    return {
        "share_id": str(share.id),
        "report_id": str(report.id),
        "title": report.title,
        "content": report.content,
        "metadata": report.metadata,
        "share_type": share.share_type,
        "view_count": share.view_count,
        "max_views": share.max_views,
        "allow_download": share.allow_download,
        "allow_export": share.allow_export,
        "created_at": share.created_at.isoformat()
    }
```

---

## Data Migration

### Migration Script (scripts/migrate_to_database.py)
```python
"""Migration script to migrate file-based data to database."""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Session, Report

def migrate_sessions(db: Session, default_user_id: str):
    """Migrate sessions from files to database."""
    sessions_dir = Path("data/research/sessions")
    for session_file in sessions_dir.glob("session_*.json"):
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Create session in database
        session = Session(
            user_id=default_user_id,
            session_id=session_data.get("metadata", {}).get("session_id"),
            batch_id=session_data.get("metadata", {}).get("batch_id"),
            status=session_data.get("status", "initialized"),
            metadata=session_data.get("metadata", {}),
            scratchpad=session_data.get("scratchpad", {}),
            phase_artifacts=session_data.get("phase_artifacts", {}),
            step_digests=session_data.get("step_digests", {})
        )
        db.add(session)
    
    db.commit()

def migrate_reports(db: Session, default_user_id: str):
    """Migrate reports from files to database."""
    reports_dir = Path("data/research/reports")
    for report_file in reports_dir.glob("report_*.md"):
        with open(report_file, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        # Extract session_id from filename
        session_id = report_file.stem.replace("report_", "")
        
        # Find session in database
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session:
            continue
        
        # Create report in database
        report = Report(
            user_id=default_user_id,
            session_id=session.id,
            batch_id=session.batch_id,
            content=report_content,
            status="published"
        )
        db.add(report)
    
    db.commit()

if __name__ == "__main__":
    db = next(get_db())
    
    # Create default user
    default_user = User(
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin123"),
        email_verified=True,
        is_active=True
    )
    db.add(default_user)
    db.commit()
    db.refresh(default_user)
    
    # Migrate data
    migrate_sessions(db, default_user.id)
    migrate_reports(db, default_user.id)
    
    print("Migration completed successfully")
```

---

## Frontend Implementation

### Authentication Context (client/src/contexts/AuthContext.tsx)
```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  email_verified: boolean;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get('/api/auth/me');
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('access_token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await axios.post('/api/auth/login', { email, password });
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    await fetchUser();
  };

  const logout = async () => {
    await axios.post('/api/auth/logout');
    localStorage.removeItem('access_token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  const register = async (email: string, username: string, password: string) => {
    await axios.post('/api/auth/register', { email, username, password });
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### Protected Route Component (client/src/components/ProtectedRoute.tsx)
```typescript
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
```

---

## Deployment Configuration

### Docker Compose (docker-compose.yml)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: research_tool
      POSTGRES_USER: research_tool_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://research_tool_user:secure_password@postgres/research_tool
      REDIS_URL: redis://redis:6379
      SECRET_KEY: your-secret-key-here
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./client
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### Nginx Configuration (nginx.conf)
```nginx
server {
    listen 80;
    server_name example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Frontend
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://backend:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://backend:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Conclusion

This implementation guide provides code examples and patterns for implementing the server migration. For the complete migration plan, see [SERVER_MIGRATION_PLAN.md](./SERVER_MIGRATION_PLAN.md).

### Next Steps
1. Set up database and Redis
2. Implement authentication system
3. Implement authorization middleware
4. Migrate existing data
5. Implement report sharing
6. Deploy to production

### Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [JWT Documentation](https://jwt.io/)

