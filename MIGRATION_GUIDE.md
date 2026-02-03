# Health Facilities Migration Guide

This guide explains how to apply the health facilities database changes.

## What's Included

This feature adds a database table for managing health facility information, replacing hardcoded emergency contacts with a dynamic, database-driven system.

### Changes Made

1. **New Database Model**: `HealthFacility` model with comprehensive facility information
2. **API Endpoints**: Admin endpoints for managing facilities
3. **Service Layer**: Health facility service for business logic
4. **Danger Signs Update**: Updated to fetch facilities from database
5. **Seed Data**: Initial data for 7 health facilities in Migori County

## Prerequisites

- Docker and Docker Compose running
- Database and backend services up

## Migration Steps

### Step 1: Start Services

```bash
make up
```

### Step 2: Generate Initial Migration

Since this is the first migration, we need to create it:

```bash
docker-compose exec backend alembic revision --autogenerate -m "Add health_facilities table"
```

This will create a migration file in `backend/alembic/versions/`

### Step 3: Apply Migration

```bash
docker-compose exec backend alembic upgrade head
```

Or using the Makefile:

```bash
make migrate
```

### Step 4: Seed Health Facilities Data

After the migration is applied, seed the initial facility data:

```bash
docker-compose exec backend python -m app.cli seed-facilities
```

### Step 5: Verify Installation

Check that facilities were created:

```bash
docker-compose exec backend python -c "
import asyncio
from app.core.database import get_db_session
from app.services.health_facility_service import health_facility_service

async def check():
    async with get_db_session() as db:
        facilities, total = await health_facility_service.get_all(db, limit=10)
        print(f'Total facilities: {total}')
        for f in facilities:
            print(f'  - {f.name} ({f.county})')

asyncio.run(check())
"
```

You should see 7 facilities listed for Migori County.

## API Usage

### List All Facilities (Admin Only)

```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' | jq -r '.access_token')

# List facilities
curl http://localhost:8001/api/v1/health-facilities \
  -H "Authorization: Bearer $TOKEN"
```

### Get Emergency Contacts for a County

```bash
curl http://localhost:8001/api/v1/health-facilities/emergency/Migori \
  -H "Authorization: Bearer $TOKEN"
```

### Create a New Facility

```bash
curl -X POST http://localhost:8001/api/v1/health-facilities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Health Center",
    "facility_type": "health_center",
    "facility_level": "level_2",
    "county": "Migori",
    "phone_number": "0700123456",
    "has_maternity_services": true,
    "has_emergency_services": true,
    "is_verified": false
  }'
```

## Testing

The danger sign detection will now automatically fetch facilities from the database:

1. Send a WhatsApp message with a danger sign keyword (e.g., "I have severe bleeding")
2. The response should include facilities from the database
3. If the database is unavailable, it falls back to hardcoded contacts

## Rollback (If Needed)

If you need to rollback the migration:

```bash
docker-compose exec backend alembic downgrade -1
```

## Troubleshooting

### Issue: "Table already exists" error

If you've run the app before without migrations, you might have tables created by SQLAlchemy. In this case:

1. Backup your data
2. Drop the `health_facilities` table if it exists
3. Run the migration again

### Issue: Seed command fails

Make sure:
- The migration has been applied first
- The database is running and accessible
- You're running the command from the backend container

### Issue: API endpoints return 404

Check that:
- The backend service has been restarted after adding new endpoints
- The router import in `app/api/router.py` is correct

## Next Steps

After successful migration:

1. **Update Admin Dashboard**: Add UI for managing facilities
2. **Add Location Support**: Track user location to show nearest facilities
3. **Add More Counties**: Seed data for additional counties
4. **Monitoring**: Monitor facility contact accuracy and update as needed

## Files Changed

- `backend/app/models/health_facility.py` - New model
- `backend/app/schemas/health_facility.py` - New schemas
- `backend/app/services/health_facility_service.py` - New service
- `backend/app/services/danger_signs.py` - Updated to use database
- `backend/app/services/conversation_handler.py` - Updated to pass db session
- `backend/app/api/endpoints/health_facilities.py` - New API endpoints
- `backend/app/api/router.py` - Added facility router
- `backend/app/seeds/health_facilities.py` - Seed data
- `backend/app/cli.py` - CLI command for seeding
- `backend/alembic/env.py` - Added model import

## Benefits

✅ No code changes needed to update facility contacts
✅ Support for multiple counties
✅ Scalable to other regions
✅ Admin can manage facilities via API
✅ Fallback to hardcoded contacts if database fails
✅ Detailed facility information (services, hours, location)
