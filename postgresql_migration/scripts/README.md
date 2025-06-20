# PostgreSQL Migration Scripts

This directory contains the active migration scripts for converting YOUTILITY3 to PostgreSQL-first architecture.

## 📁 Active Scripts

### `phase1_rate_limiting.py`
**Purpose:** Migrate rate limiting from Redis to PostgreSQL
**Status:** ✅ Complete and deployed
**Usage:**
```bash
python postgresql_migration/scripts/phase1_rate_limiting.py
```
**What it does:**
- Creates `auth_rate_limit_attempts` table
- Sets up PostgreSQL functions for rate limiting
- Implements username-based blocking (5 attempts)
- Sets up IP-based fallback (15 attempts)

### `session_optimization.py`
**Purpose:** Optimize PostgreSQL sessions and create cleanup mechanisms
**Status:** ✅ Complete and deployed
**Usage:**
```bash
python postgresql_migration/scripts/session_optimization.py
```
**What it does:**
- Creates performance indexes on `django_session` table
- Sets up automated cleanup functions
- Creates Django management command for manual cleanup
- Optimizes session storage for performance

### `session_cleanup_setup.py`
**Purpose:** Set up automated session cleanup with Celery
**Status:** ✅ Complete and deployed
**Usage:**
```bash
python postgresql_migration/scripts/session_cleanup_setup.py
```
**What it does:**
- Creates Celery task for session cleanup
- Sets up periodic task (every 6 hours)
- Adds automation to prevent session table bloat

## 🔄 Future Scripts (Phase 1B)

### `select2_migration.py` (Planned)
**Purpose:** Migrate Select2 caching from Redis to PostgreSQL
**Status:** 📋 Planned for Phase 1B
**Target:** Replace `select2` Redis cache with PostgreSQL-based caching

## 🚀 Usage Examples

### Complete PostgreSQL Migration
```bash
# Run all Phase 1 scripts (if starting fresh)
cd /path/to/YOUTILITY3
python postgresql_migration/scripts/phase1_rate_limiting.py
python postgresql_migration/scripts/session_optimization.py
python postgresql_migration/scripts/session_cleanup_setup.py
```

### Verification
```bash
# Test the implementations
python postgresql_migration/tests/session_testing.py
python manage.py cleanup_sessions --dry-run
```

## ⚠️ Important Notes

1. **Order Matters:** Run scripts in the order listed above
2. **Database Backup:** Always backup before running migration scripts
3. **Testing:** Scripts include built-in testing and validation
4. **Idempotent:** Scripts can be run multiple times safely
5. **Production Ready:** All scripts have been tested and validated

## 📊 Script Status Dashboard

| Script | Status | Performance | Dependencies Removed |
|--------|--------|-------------|---------------------|
| Rate Limiting | ✅ Complete | Database-native | Redis rate limiting |
| Session Optimization | ✅ Complete | 1.89ms avg | Redis session cache |
| Session Cleanup | ✅ Complete | Automated | Manual maintenance |
| Select2 Migration | 📋 Planned | TBD | Redis select2 cache |

## 🔧 Maintenance

These scripts create self-maintaining systems:
- **Rate Limiting:** Auto-cleanup via PostgreSQL functions
- **Sessions:** Auto-cleanup via Celery every 6 hours
- **Monitoring:** Built-in logging and status reporting

## 🚨 Rollback Information

If needed, rollback procedures:
1. **Rate Limiting:** Restore original middleware configuration
2. **Sessions:** Change `SESSION_ENGINE` back to `cached_db`
3. **Cleanup:** Disable Celery periodic tasks

All changes are database-additive and don't remove existing functionality.