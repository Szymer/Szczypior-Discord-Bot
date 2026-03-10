"""
Deploy PostgreSQL schema to Supabase
Run: python tools/deploy_schema.py
"""

import asyncio
import asyncpg
import os
from pathlib import Path


async def deploy_schema():
    """Deploy schema from init.sql to database."""
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set in environment")
        print("Add to .env file:")
        print("DATABASE_URL=postgresql://postgres:XjQFUjFcMGkRsqhq@db.wpvjryhrhigqqccblkav.supabase.co:5432/postgres")
        return False
    
    # Read schema file
    schema_path = Path(__file__).parent.parent / "infrastructure" / "postgres" / "init.sql"
    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return False
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    print(f"📄 Read schema from: {schema_path}")
    print(f"📦 Schema size: {len(schema_sql)} characters")
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    try:
        # Execute schema
        print("\n🚀 Deploying schema...")
        await conn.execute(schema_sql)
        print("✅ Schema deployed successfully!")
        
        # Verify tables
        print("\n🔍 Verifying tables...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Verify views
        print("\n🔍 Verifying views...")
        views = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"✅ Found {len(views)} views:")
        for view in views:
            print(f"   - {view['table_name']}")
        
        # Check seed data
        print("\n🔍 Verifying seed data...")
        missions = await conn.fetch("SELECT name, emoji, bonus_points FROM special_missions")
        
        if missions:
            print(f"✅ Found {len(missions)} special missions:")
            for mission in missions:
                print(f"   - {mission['emoji']} {mission['name']} (+{mission['bonus_points']} pts)")
        else:
            print("⚠️  No special missions found")
        
        print("\n✅ Database is ready to use!")
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await conn.close()
        print("\n🔌 Connection closed")


async def test_connection():
    """Test database connection only."""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    print("🔌 Testing connection...")
    try:
        conn = await asyncpg.connect(database_url)
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Connection successful!")
        print(f"📊 PostgreSQL version: {version}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Parse command
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_connection())
    else:
        asyncio.run(deploy_schema())
