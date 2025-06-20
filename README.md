# YOUTILITY3 - Enterprise Facility Management System

**Version**: Django 5.2 Production-Ready Build  
**Type**: Multi-tenant Facility Management & IoT Platform  
**Security Status**: Phase 1 Hardened (Production Ready)  

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Security Features](#security-features)
- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Core Applications](#core-applications)
- [API Documentation](#api-documentation)
- [Security Implementation](#security-implementation)
- [Development Guidelines](#development-guidelines)
- [Production Deployment](#production-deployment)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

YOUTILITY3 is a comprehensive Django-based enterprise facility management system designed for multi-tenant environments. Originally built for security guards and facility management teams, it provides real-time monitoring, asset tracking, work order management, and comprehensive reporting capabilities.

### Key Features

- **Multi-tenant Architecture**: Isolated data and configurations per client
- **Mobile-First Design**: Optimized for field workers and security personnel
- **Real-time IoT Integration**: MQTT-based device communication
- **Comprehensive Reporting**: PDF generation with WeasyPrint
- **GraphQL API**: Modern API layer for mobile applications
- **Background Task Processing**: Celery-based asynchronous operations
- **Advanced Security**: Rate limiting, session management, and audit logging

### Business Context

- **Primary Users**: Security guards, facility managers, maintenance teams
- **Use Cases**: Site monitoring, preventive maintenance, work permits, attendance tracking
- **Scale**: Enterprise-level with multi-site support
- **Integration**: ERP systems, IoT devices, mobile applications

---

## Architecture

### Technology Stack

```
Frontend Layer:
├── Django Templates (Jinja2 + Django)
├── Bootstrap 4.x UI Framework
├── DataTables for grid interfaces
├── Leaflet.js for mapping
└── Select2 for enhanced forms

Backend Layer:
├── Django 5.2 (Web Framework)
├── PostgreSQL + PostGIS (Database)
├── Redis (Cache & Message Broker)
├── Celery (Background Tasks)
├── GraphQL (API Layer)
└── WeasyPrint (PDF Generation)

Infrastructure:
├── Docker Support
├── WhiteNoise (Static Files)
├── Gunicorn (WSGI Server)
├── MQTT (IoT Communication)
└── Google Cloud Storage
```

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    
│   Mobile Apps   │    │   Web Interface │    
│   (GraphQL)     │    │   (Django)      │    
└─────────┬───────┘    └─────────┬───────┘              │                      │                      │
          └──────────────────────         ┼─────────
                                 │
                    ┌─────────────▼───────────────┐
                    │      YOUTILITY3 Core       │
                    │                             │
                    │  ┌─────────┐ ┌─────────┐   │
                    │  │ GraphQL │ │ REST API│   │
                    │  └─────────┘ └─────────┘   │
                    │                             │
                    │  ┌─────────────────────┐   │
                    │  │   Django Apps       │   │
                    │  │ ┌─────┐ ┌─────────┐ │   │
                    │  │ │Auth │ │Business │ │   │
                    │  │ └─────┘ └─────────┘ │   │
                    │  └─────────────────────┘   │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │     Data & Cache Layer      │
                    │                             │
                    │ ┌─────────┐ ┌─────────────┐ │
                    │ │PostgreSQL│ │   Redis     │ │
                    │ │ PostGIS  │ │(Cache/Queue)│ │
                    │ └─────────┘ └─────────────┘ │
                    └─────────────────────────────┘
```

---

## Security Features

### 🔒 Implemented Security Hardening (Phase 1)

#### Authentication & Authorization
- **Multi-layer Rate Limiting**: IP-based (5/5min) + Username-based (3/30min)
- **Secure Session Management**: HTTPS-only cookies, secure tokens
- **Brute Force Protection**: Automatic account/IP lockouts
- **Authentication Backend**: Cleaned and hardened (removed broken backends)

#### Environment Security
- **4-Tier Environment System**: dev, dev.secure, prod, prod.secure
- **Environment-Driven Configuration**: Security settings via environment variables
- **Secret Management**: Secure key generation and storage
- **Debug Control**: Environment-specific debug modes

#### Security Headers & Protection
- **HSTS**: HTTP Strict Transport Security
- **CSP**: Content Security Policy
- **XSS Protection**: Browser-level XSS filtering
- **CSRF Protection**: Secure cross-site request forgery prevention
- **Clickjacking Protection**: X-Frame-Options headers

#### Monitoring & Logging
- **Security Event Logging**: Failed login attempts, rate limit violations
- **Audit Trail**: User action tracking and session monitoring
- **Performance Monitoring**: Application and database performance tracking
- **Error Tracking**: Comprehensive error logging and alerting

### 🔒 Security Configuration Files

```
intelliwiz_config/envs/
├── .env.dev          # Development (DEBUG=True)
├── .env.dev.secure   # Secure development testing
├── .env.prod         # Current production
└── .env.prod.secure  # Production-ready secure config
```

---

## Installation & Setup

### Prerequisites

```bash
# System Requirements
Python 3.12+
PostgreSQL 14+ with PostGIS
Redis 6+
Node.js 16+ (for frontend assets)

# Development Tools
Git
Docker (optional)
```

### Quick Start

```bash
# 1. Clone Repository
git clone <repository-url>
cd YOUTILITY3

# 2. Create Virtual Environment
python -m venv env
source env/bin/activate  # Linux/Mac
env\Scripts\activate     # Windows

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Environment Setup
cp intelliwiz_config/envs/.env.dev.example intelliwiz_config/envs/.env.dev
# Edit .env.dev with your configuration

# 5. Database Setup
python manage.py migrate

# 6. Create Superuser
python manage.py createsuperuser

# 7. Start Development Server
python manage.py runserver

# 8. Start Celery Worker (separate terminal)
celery -A intelliwiz_config worker -l info

# 9. Start Celery Beat (separate terminal)
celery -A intelliwiz_config beat -l info
```

### Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

---

## Environment Configuration

### Switching Between Environments

In `intelliwiz_config/settings.py`, change line 36:

```python
# Development (insecure, easy debugging)
ENV_FILE = '.env.dev'

# Secure development (testing security features)
ENV_FILE = '.env.dev.secure'

# Current production
ENV_FILE = '.env.prod'

# Secure production (recommended for production)
ENV_FILE = '.env.prod.secure'
```

### Environment Variables

#### Core Settings
```bash
# Security
DEBUG=False
SECRET_KEY=your-secure-secret-key
ENCRYPT_KEY=your-encryption-key

# Database
DBUSER=your-db-user
DBPASS=your-db-password
DBHOST=your-db-host
DBNAME=your-db-name

# Cache & Queue
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
result_backend=redis://127.0.0.1:6379/1
```

#### Security Features
```bash
# HTTPS Security (production only)
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
ENABLE_SECURITY_HEADERS=True

# File Storage
MEDIA_ROOT=/var/tmp/youtility4_media
STATIC_ROOT=/var/www/static
```

#### External Services
```bash
# Google Services
GOOGLE_MAP_SECRET_KEY=your-google-maps-key
BULK_IMPORT_GOOGLE_DRIVE_API_KEY=your-drive-api-key

# Email Configuration
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# MQTT (IoT Integration)
MQTT_BROKER_ADDRESS=your-mqtt-broker
MQTT_BROKER_PORT=1883
MQTT_BROKER_USERNAME=your-mqtt-user
MQTT_BROKER_PASSWORD=your-mqtt-password
```

---

## Core Applications

### 🏢 Business Domain Apps

#### peoples
**Purpose**: User management, authentication, and capabilities
```
├── models.py          # User profiles, groups, capabilities
├── views.py           # Authentication, user management
├── forms.py           # User creation, login forms
├── managers.py        # Custom user managers
└── backends.py        # Authentication backends (removed in v1.2)
```

**Key Features**:
- Custom user model with tenant isolation
- Role-based access control
- Group and capability management
- Secure authentication with rate limiting

#### onboarding
**Purpose**: Client setup, business types, and site configuration
```
├── models.py          # Clients, business units, type assists
├── views.py           # Client onboarding workflows
├── forms.py           # Client setup forms
├── managers.py        # Business logic managers
└── middlewares.py     # Tenant routing, timezone handling
```

**Key Features**:
- Multi-tenant client setup
- Business unit configuration
- Site and location management
- Type assist configuration

#### activity
**Purpose**: Assets, locations, questions, jobs, and device events
```
├── models/            # Domain models (assets, jobs, questions)
├── views/             # CRUD operations for activities
├── forms/             # Activity-related forms
├── managers/          # Business logic for activities
└── admin/             # Django admin configuration
```

**Key Features**:
- Asset lifecycle management
- Location and checkpoint tracking
- Question sets and surveys
- Job scheduling and execution
- Device event logging

#### attendance
**Purpose**: People tracking, geofencing, and SOS functionality
```
├── models.py          # Attendance, geofence, SOS models
├── views.py           # Attendance tracking views
├── attd_capture.py    # Attendance capture logic
└── managers.py        # Attendance business logic
```

**Key Features**:
- Real-time location tracking
- Geofence monitoring
- SOS emergency features
- Attendance reporting

### 🔧 Technical Apps

#### service
**Purpose**: GraphQL API layer for mobile applications
```
├── schema.py          # Main GraphQL schema
├── queries/           # GraphQL query resolvers
├── mutations.py       # GraphQL mutation resolvers
├── types.py           # GraphQL type definitions
├── auth.py            # API authentication logic
└── pydantic_schemas/  # Data validation schemas
```

**API Endpoints**:
- `/graphql/` - Main GraphQL endpoint
- `/api/` - REST API endpoints
- Authentication via JWT tokens

#### reports
**Purpose**: PDF generation and scheduled reporting
```
├── models.py          # Report definitions
├── views.py           # Report generation views
├── report_designs/    # PDF report templates
└── utils.py           # Report utilities
```

**Report Types**:
- Site visit reports
- Attendance summaries
- Asset status reports
- Work order lists
- QR code reports

#### schedhuler
**Purpose**: Tour scheduling, PPM management, task automation
```
├── models.py          # Schedule definitions
├── views.py           # Schedule management
├── utils.py           # Scheduling algorithms
└── utils_new.py       # Enhanced scheduling logic
```

**Features**:
- Preventive maintenance scheduling
- Tour route optimization
- Task automation
- Calendar integration

---

## API Documentation

### GraphQL API

#### Authentication
```graphql
mutation {
  tokenAuth(loginid: "username", password: "password", clientcode: "CLIENT") {
    token
    refreshToken
    user {
      id
      peoplename
      loginid
    }
  }
}
```

#### Common Queries
```graphql
# Get user profile
query {
  me {
    id
    peoplename
    client {
      buname
    }
    bu {
      buname
    }
  }
}

# Get assets
query {
  assets(first: 10) {
    edges {
      node {
        id
        assetname
        assetcode
        location {
          locname
        }
      }
    }
  }
}

# Get jobs
query {
  jobs(status: "ACTIVE") {
    edges {
      node {
        id
        jobname
        status
        assignedTo {
          peoplename
        }
      }
    }
  }
}
```

#### Common Mutations
```graphql
# Create job need
mutation {
  createJobneed(input: {
    jobId: 1
    locationId: 1
    assignedTo: 1
    description: "Maintenance task"
  }) {
    jobneed {
      id
      status
    }
  }
}

# Update attendance
mutation {
  updateAttendance(input: {
    peopleId: 1
    latitude: 12.345
    longitude: 67.890
    timestamp: "2024-01-01T10:00:00Z"
  }) {
    attendance {
      id
      status
    }
  }
}
```

### REST API

#### Endpoints
```
GET  /api/people/           # List people
POST /api/people/           # Create person
GET  /api/assets/           # List assets
POST /api/reports/generate/ # Generate report
GET  /api/health/           # Health check
```

---

## Security Implementation

### Rate Limiting

#### Configuration
```python
# apps/core/rate_limiting.py

# IP-based rate limiting
IP_RATE_LIMIT = 5       # attempts
IP_WINDOW = 300         # 5 minutes

# Username-based rate limiting  
USER_RATE_LIMIT = 3     # attempts
USER_WINDOW = 1800      # 30 minutes
```

#### Usage Example
```python
from apps.core.rate_limiting import rate_limit_login, record_failed_login

class LoginView(View):
    @rate_limit_login(max_attempts=5, window=300)
    def post(self, request):
        # Login logic
        if not authenticated:
            record_failed_login(request, username)
```

### Session Security

#### Settings
```python
# Secure session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'redis_session_cache'
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour
```

### HTTPS & Security Headers

#### Production Configuration
```python
# Security headers (enabled in .env.prod.secure)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

---

## Development Guidelines

### Code Style

#### Python Code Standards
```python
# Class names: PascalCase
class AssetManager:
    pass

# Function names: snake_case
def get_asset_by_code(asset_code):
    pass

# Variable names: snake_case
user_profile = get_user_profile()

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
```

#### Import Order
```python
# 1. Python standard library
import os
import logging
from datetime import datetime

# 2. Django core
from django.db import models
from django.contrib.auth import authenticate

# 3. Third-party packages
import requests
from celery import shared_task

# 4. Local application imports
from apps.peoples.models import People
from apps.core.utils import get_client_ip
```

### Template Naming Conventions
```
templates/
├── app_name/
│   ├── model_list.html      # Grid/list views
│   ├── model_form.html      # Create/edit forms
│   └── model_detail.html    # Detail views
```

### Testing Strategy

#### Test Structure
```
apps/app_name/tests/
├── __init__.py
├── conftest.py              # Pytest configuration
├── test_models.py           # Model tests
├── test_views.py            # View tests
├── test_forms.py            # Form tests
└── test_utils.py            # Utility tests
```

#### Running Tests
```bash
# Run all tests
pytest

# Run specific app tests
pytest apps/peoples/tests/

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test
pytest apps/peoples/tests/test_models.py::TestPeopleModel::test_create_user
```

### Database Migrations

#### Creating Migrations
```bash
# Create migrations for specific app
python manage.py makemigrations peoples

# Create empty migration for data migration
python manage.py makemigrations --empty peoples

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

---

## Production Deployment

### Server Requirements

#### Minimum Hardware
```
CPU: 4 cores
RAM: 8GB
Storage: 100GB SSD
Network: 1Gbps
```

#### Recommended Hardware
```
CPU: 8 cores
RAM: 16GB
Storage: 500GB SSD
Network: 1Gbps
Database: Separate PostgreSQL server
Cache: Separate Redis server
```

### Deployment Steps

#### 1. Server Preparation
```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.12 python3.12-venv postgresql-14 redis-server nginx

# Create application user
useradd -m -s /bin/bash youtility
```

#### 2. Application Setup
```bash
# Switch to application user
su - youtility

# Clone repository
git clone <repository-url> youtility3
cd youtility3

# Create virtual environment
python3.12 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

#### 3. Configuration
```bash
# Configure environment
cp intelliwiz_config/envs/.env.prod.secure intelliwiz_config/envs/.env.prod
# Edit .env.prod with production values

# Update settings.py
ENV_FILE = '.env.prod'

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
```

#### 4. Services Setup

#### Gunicorn Service
```ini
# /etc/systemd/system/youtility3.service
[Unit]
Description=YOUTILITY3 Gunicorn Application Server
After=network.target

[Service]
User=youtility
Group=youtility
WorkingDirectory=/home/youtility/youtility3
Environment=PATH=/home/youtility/youtility3/env/bin
ExecStart=/home/youtility/youtility3/env/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/youtility3/access.log \
    --error-logfile /var/log/youtility3/error.log \
    intelliwiz_config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Celery Worker Service
```ini
# /etc/systemd/system/youtility3-celery.service
[Unit]
Description=YOUTILITY3 Celery Worker
After=network.target

[Service]
User=youtility
Group=youtility
WorkingDirectory=/home/youtility/youtility3
Environment=PATH=/home/youtility/youtility3/env/bin
ExecStart=/home/youtility/youtility3/env/bin/celery -A intelliwiz_config worker -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Celery Beat Service
```ini
# /etc/systemd/system/youtility3-celerybeat.service
[Unit]
Description=YOUTILITY3 Celery Beat Scheduler
After=network.target

[Service]
User=youtility
Group=youtility
WorkingDirectory=/home/youtility/youtility3
Environment=PATH=/home/youtility/youtility3/env/bin
ExecStart=/home/youtility/youtility3/env/bin/celery -A intelliwiz_config beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 5. Nginx Configuration
```nginx
# /etc/nginx/sites-available/youtility3
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/youtility/youtility3/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/tmp/youtility4_media/;
        expires 7d;
    }
}
```

#### 6. Start Services
```bash
# Enable and start services
systemctl enable youtility3 youtility3-celery youtility3-celerybeat nginx
systemctl start youtility3 youtility3-celery youtility3-celerybeat nginx

# Check status
systemctl status youtility3
systemctl status youtility3-celery
systemctl status youtility3-celerybeat
```

### SSL Certificate Setup

#### Using Let's Encrypt
```bash
# Install Certbot
apt install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d your-domain.com

# Test auto-renewal
certbot renew --dry-run
```

---

## Monitoring & Logging

### Log Configuration

The application uses structured logging with multiple handlers:

```python
LOGGING_CONFIG = {
    'handlers': {
        'filelogs': {
            'filename': f'{LOGGER_PATH}/youtility4_logs/youtility4.log',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 15728640,  # 15MB
            'backupCount': 10,
        },
        'error_file_handler': {
            'filename': f'{LOGGER_PATH}/youtility4_logs/errors.log',
            'level': 'ERROR',
        },
        'security_logs': {
            'filename': f'{LOGGER_PATH}/youtility4_logs/security.log',
            'level': 'WARNING',
        }
    }
}
```

### Log Files

```
youtility4_logs/
├── youtility4.log      # General application logs
├── debug.log           # Debug information
├── errors.log          # Error tracking
├── security.log        # Security events
├── tracking.log        # Location tracking
├── mobileservice.log   # Mobile API logs
├── message_q.log       # Queue operations
└── reports.log         # Report generation
```

### Health Checks

#### Application Health
```python
# apps/core/health.py
def health_check():
    checks = {
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'celery': check_celery_status(),
        'disk_space': check_disk_space(),
    }
    return all(checks.values()), checks
```

#### Monitoring Endpoints
```
GET /health/           # Basic health check
GET /health/detailed/  # Detailed system status
GET /metrics/          # Prometheus metrics (if enabled)
```

### Performance Monitoring

#### Database Query Monitoring
```python
# Enable in development
SHELL_PLUS_PRINT_SQL = True

# Log slow queries in production
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['slow_queries'],
        }
    }
}
```

#### Celery Monitoring
```bash
# Monitor Celery with Flower
celery -A intelliwiz_config flower

# Access web interface
# http://localhost:5555
```

---

## Troubleshooting

### Common Issues

#### 1. Authentication Issues
```bash
# Check rate limiting status
redis-cli keys "rate_limit:*"

# Clear rate limiting
redis-cli flushall

# Reset user password
python manage.py shell
>>> from apps.peoples.models import People
>>> user = People.objects.get(loginid='username')
>>> user.set_password('newpassword')
>>> user.save()
```

#### 2. Database Connection Issues
```python
# Test database connection
python manage.py dbshell

# Check database settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DATABASES)
```

#### 3. Celery Issues
```bash
# Check Celery worker status
celery -A intelliwiz_config inspect active

# Purge queue
celery -A intelliwiz_config purge

# Check Redis connection
redis-cli ping
```

#### 4. Static Files Issues
```bash
# Collect static files
python manage.py collectstatic --clear

# Check static files configuration
python manage.py findstatic admin/css/base.css
```

#### 5. Permission Issues
```bash
# Fix file permissions
chown -R youtility:youtility /home/youtility/youtility3
chmod -R 755 /home/youtility/youtility3

# Fix media directory permissions
chown -R youtility:www-data /var/tmp/youtility4_media
chmod -R 775 /var/tmp/youtility4_media
```

### Debug Commands

#### Django Debug
```bash
# Check system configuration
python manage.py check

# Run with debug
python manage.py runserver --debug

# Shell with models loaded
python manage.py shell_plus

# Show URLs
python manage.py show_urls
```

#### Database Debug
```bash
# Show migrations
python manage.py showmigrations

# Create migration for existing schema
python manage.py makemigrations --empty app_name

# Reverse migration
python manage.py migrate app_name 0001
```

### Log Analysis

#### Common Log Patterns
```bash
# Security events
grep "rate limit\|failed login\|blocked" youtility4_logs/security.log

# Database errors
grep "ERROR.*database" youtility4_logs/errors.log

# Performance issues
grep "slow\|timeout" youtility4_logs/youtility4.log

# Celery task failures
grep "FAILURE\|ERROR" youtility4_logs/message_q.log
```

---

## Contributing

### Development Workflow

#### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... development work ...

# Run tests
pytest

# Check code quality
python manage.py check --deploy

# Commit changes
git add .
git commit -m "Add new feature: description"
```

#### 2. Code Review Process
- All changes require pull request review
- Security-related changes require additional review
- Tests must pass before merging
- Documentation updates required for new features

#### 3. Security Guidelines
- Never commit secrets or API keys
- Always use environment variables for configuration
- Follow security best practices for authentication
- Regular security audits and updates

### Project Structure Best Practices

#### Adding New Apps
```bash
# Create new app
python manage.py startapp new_app apps/new_app

# Update structure
mkdir apps/new_app/{models,views,forms,managers,tests}
```

#### Model Guidelines
```python
# Always inherit from TenantAwareModel for multi-tenancy
class NewModel(TenantAwareModel):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'new_model'
        ordering = ['-created_at']
```

#### Security Considerations
- All user inputs must be validated
- Use Django ORM to prevent SQL injection
- Implement proper authorization checks
- Follow principle of least privilege

---

## License

This project is proprietary software. All rights reserved.

**Copyright (c) 2024 YOUTILITY**

For licensing inquiries, contact: [licensing@youtility.com]

---

## Support & Contact

### Technical Support
- **Email**: support@youtility.com
- **Documentation**: [Internal Wiki]
- **Issue Tracking**: [Internal Issue Tracker]

### Development Team
- **Lead Developer**: [Team Lead]
- **DevOps Engineer**: [DevOps Team]

### Security Contact
For security vulnerabilities, contact: security@youtility.com

---

**Last Updated**: 2025-06-18  
**Documentation Version**: 1.2  
**Application Version**: Django 5.2 Production-Ready Build# youtility_django_5.2_with_postgresql_first_approach
# youtility_django_5.2_with_postgresql_first_approach
