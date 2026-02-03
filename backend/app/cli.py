"""CLI commands for database management and seeding."""

import asyncio

import click


@click.group()
def cli():
    """Database management commands."""
    pass


@cli.command()
def seed_facilities():
    """Seed health facilities data."""
    from app.core.database import get_db_session
    from app.seeds.health_facilities import seed_health_facilities

    async def run_seed():
        async with get_db_session() as db:
            print("Seeding health facilities...")
            await seed_health_facilities(db)
            print("✓ Done!")

    asyncio.run(run_seed())


if __name__ == "__main__":
    cli()
