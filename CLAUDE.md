# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YOUTILITY3 is a Django 5.2 enterprise facility management application originally built by junior developers. The codebase is functional but may not follow all production best practices yet.

**Key Characteristics:**
- **Multi-tenant architecture** with tenant-aware models
- **GraphQL API** using Graphene-Django for mobile/external integrations
- **Celery background tasks** for scheduled operations (PPM, notifications, reports)
- **Modular app structure** with 12+ Django apps for different business domains
- **PostgreSQL database** with Redis for caching and Celery broker
- **WeasyPrint PDF generation** for reports and work permits

**Code Quality Notes:**
- Codebase is evolving from early-stage development to production-ready
- Some areas may have technical debt or non-standard patterns
- Focus on gradual improvement while maintaining functionality

## Common Development Commands

### Django Management
```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Django shell
python manage.py shell
```

### Testing
```bash
# Run all tests
pytest

# Run specific app tests
pytest apps/activity/tests/

# Run with coverage
pytest --cov=apps
```

### Celery Background Tasks
```bash
# Start Celery worker
celery -A intelliwiz_config worker -l info

# Start Celery beat scheduler
celery -A intelliwiz_config beat -l info

# Monitor Celery tasks
celery -A intelliwiz_config flower
```

### Documentation Generation
```bash
# Generate GraphQL schema documentation
npm run generate-docs
```

## Architecture Overview

### App Structure
The project follows Django's app-based architecture with clear separation of concerns:

- **peoples**: User management, capabilities, groups, authentication
- **onboarding**: Client setup, business types, type assists, site configuration
- **activity**: Assets, locations, questions, jobs, device events
- **attendance**: People tracking, geofencing, SOS functionality
- **schedhuler**: Tour scheduling, PPM management, task automation
- **work_order_management**: Work permits, SLAs, vendor management
- **y_helpdesk**: Ticketing system with escalation
- **reports**: PDF generation, scheduled reports, email delivery
- **service**: GraphQL API layer with queries/mutations
- **tenants**: Multi-tenancy support with tenant-aware models

### Key Patterns

1. **Modular Organization**: Each app has separate directories for models, views, forms, managers, tests
2. **Tenant Isolation**: Most models inherit from TenantAwareModel for multi-tenancy
3. **Background Processing**: Celery handles scheduled tasks like PPM creation, notifications, report generation
4. **API Layer**: GraphQL provides mobile API access with JWT authentication
5. **PDF Reports**: WeasyPrint generates work permits, attendance reports, tour summaries

### Database Configuration
- Primary: PostgreSQL with psycopg2/psycopg3
- Cache/Broker: Redis for Django cache and Celery message broker
- Environment-based settings in `intelliwiz_config/envs/.env.dev`

### Frontend Assets
- Static files in `frontend/static/`
- Custom CSS/JS in `assets/css/local/` and `assets/js/local/`
- DataTables, Leaflet maps, Select2 for enhanced UI components

## Development Guidelines

### Code Style (from project_essentials.md)
- Class names: PascalCase
- Function/method names: snake_case
- Variable names: snake_case
- Template naming: `<name>_list.html` for grids, `<name>_form.html` for forms
- Import order: Python standard → Django core → Third-party → Project-level

### Testing Strategy
- Use pytest with Django settings module configured
- Test files: `test_*.py`, `*_tests.py`, `tests.py`
- Comprehensive test coverage for models, forms, managers, views

### Environment Setup
- Development settings: `intelliwiz_config.settings` (points to `.env.dev`)
- Production: Change to `.env.prod` and `production_settings`
- Required environment variables include database, Redis, Google Maps API, cloud storage keys