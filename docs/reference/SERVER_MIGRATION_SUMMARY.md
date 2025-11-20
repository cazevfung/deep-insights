# Server Migration Summary

## Quick Overview

This document provides a quick reference for the server migration plan. For detailed information, see [SERVER_MIGRATION_PLAN.md](./SERVER_MIGRATION_PLAN.md).

## Current System

- **Storage**: File-based (JSON/Markdown files)
- **Authentication**: None
- **User Isolation**: None
- **Report Sharing**: OSS-based public sharing only
- **Deployment**: Local development

## Target System

- **Storage**: PostgreSQL database + Redis cache + OSS/S3
- **Authentication**: JWT tokens with refresh tokens
- **User Isolation**: Full user isolation with ownership checks
- **Report Sharing**: Multiple share types (public, unlisted, private, password-protected)
- **Deployment**: Cloud-hosted with Docker containers

## Key Components

### Database
- **PostgreSQL**: Primary database for users, sessions, reports, shares
- **Redis**: Cache for sessions, tokens, and temporary data
- **OSS/S3**: Object storage for file assets

### Authentication
- **JWT Access Tokens**: Short-lived (15 minutes)
- **Refresh Tokens**: Long-lived (7 days), stored in database
- **Password Hashing**: bcrypt with cost factor 12
- **Email Verification**: Required for new users

### Authorization
- **User Ownership**: All resources are owned by users
- **Resource Access**: Strict user_id filtering on all queries
- **Share Access**: Token-based access with expiration and limits

### Report Sharing
- **Public**: Anyone with link can access
- **Unlisted**: Accessible via link, not discoverable
- **Private (Password)**: Requires password to access
- **Private (User)**: Only specific users can access

## Migration Phases

### Phase 1: Foundation (Weeks 1-2)
- Set up database and Redis
- Implement user authentication
- Create database schema

### Phase 2: Data Migration (Weeks 3-4)
- Migrate existing sessions to database
- Migrate existing reports to database
- Validate migrated data

### Phase 3: Authorization (Weeks 5-6)
- Implement user isolation
- Add authorization middleware
- Update all API endpoints

### Phase 4: Report Sharing (Weeks 7-8)
- Implement share system backend
- Implement share system frontend
- Test share functionality

### Phase 5: Deployment (Weeks 9-10)
- Set up cloud infrastructure
- Deploy application to staging
- Deploy to production

### Phase 6: Testing & Optimization (Weeks 11-12)
- Comprehensive testing
- Performance optimization
- Security auditing

## Database Schema

### Core Tables
- `users` - User accounts
- `sessions` - Research sessions
- `reports` - Generated reports
- `report_shares` - Share configurations
- `share_access_logs` - Share access tracking
- `user_sessions` - JWT refresh tokens

## API Changes

### New Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/shares` - Create share
- `GET /api/shares/{share_token}` - Get share info
- `PATCH /api/shares/{share_id}` - Update share
- `DELETE /api/shares/{share_id}` - Delete share

### Modified Endpoints
- All `/api/sessions/*` endpoints now require authentication
- All `/api/reports/*` endpoints now require authentication
- All `/api/workflow/*` endpoints now require authentication
- All endpoints now filter by user_id

## Security Features

### Authentication Security
- Password hashing with bcrypt (cost factor 12)
- JWT tokens with RS256 algorithm
- Short-lived access tokens (15 minutes)
- Long-lived but revocable refresh tokens (7 days)
- Rate limiting on login attempts (5 per 15 minutes)

### Authorization Security
- Strict user_id filtering on all queries
- Resource ownership verification
- Cryptographically secure share tokens
- Share expiration and view limits
- Access logging for all shares

### Data Security
- Data encryption at rest
- TLS 1.3 for all communications
- SQL injection prevention (parameterized queries)
- XSS prevention (input sanitization, CSP headers)
- Input validation on all user inputs

## Deployment Strategy

### Development
- Docker Compose for local development
- PostgreSQL and Redis in Docker containers
- Local filesystem or MinIO for storage

### Staging
- Cloud server (similar to production)
- Managed PostgreSQL and Redis services
- S3/OSS bucket for staging

### Production
- Cloud server with load balancing
- Managed PostgreSQL with read replicas
- Managed Redis with cluster mode
- S3/OSS bucket for production
- CDN for static assets
- Comprehensive monitoring and logging
- Automated database backups

## Key Decisions

### Database Choice: PostgreSQL
- **Reason**: Robust, feature-rich, excellent JSON support
- **Alternative Considered**: MySQL (rejected due to JSON support limitations)

### Authentication: JWT + Refresh Tokens
- **Reason**: Stateless, scalable, industry standard
- **Alternative Considered**: Session-based (rejected due to scalability concerns)

### Share Tokens: Cryptographically Secure Random
- **Reason**: URL-safe, unguessable, sufficient length
- **Alternative Considered**: UUID (rejected due to length and URL safety)

### Password Hashing: bcrypt
- **Reason**: Industry standard, adjustable cost factor
- **Alternative Considered**: Argon2 (rejected due to complexity)

## Migration Checklist

### Pre-Migration
- [ ] Backup all existing data
- [ ] Test migration on staging environment
- [ ] Document migration process
- [ ] Create rollback plan
- [ ] Notify users of migration

### Migration
- [ ] Set up production database
- [ ] Run database migrations
- [ ] Migrate user data
- [ ] Migrate session data
- [ ] Migrate report data
- [ ] Validate migrated data
- [ ] Deploy application to production
- [ ] Test all functionality

### Post-Migration
- [ ] Verify all data is migrated
- [ ] Test all API endpoints
- [ ] Test authentication and authorization
- [ ] Test report sharing
- [ ] Monitor system performance
- [ ] Gather user feedback

## Risk Mitigation

### Technical Risks
- **Data Loss**: Comprehensive backups, test migrations on staging
- **Performance Issues**: Load testing, database optimization, caching
- **Security Vulnerabilities**: Security audits, penetration testing, regular updates
- **Database Failures**: Database backups, replication, monitoring

### Business Risks
- **User Adoption**: User education, smooth migration process
- **Downtime**: Blue-green deployment, rollback strategy
- **Cost Overruns**: Cost monitoring, resource optimization

## Timeline

- **Total Duration**: 12 weeks
- **Phase 1**: Weeks 1-2 (Foundation)
- **Phase 2**: Weeks 3-4 (Data Migration)
- **Phase 3**: Weeks 5-6 (Authorization)
- **Phase 4**: Weeks 7-8 (Report Sharing)
- **Phase 5**: Weeks 9-10 (Deployment)
- **Phase 6**: Weeks 11-12 (Testing & Optimization)

## Next Steps

1. Review and approve migration plan
2. Assign team members to each phase
3. Set up development and staging environments
4. Begin Phase 1 implementation
5. Regular progress reviews and adjustments

## Questions?

For detailed information, see [SERVER_MIGRATION_PLAN.md](./SERVER_MIGRATION_PLAN.md).

