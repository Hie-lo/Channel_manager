"""
Script to check for duplicate customer records in the database
Run this to diagnose the MultipleResultsFound issue
"""
import asyncio
from sqlalchemy import select, func
from app.database.connection import AsyncSessionLocal
from app.database.models import Customer, Channel, PostedMessage

async def check_duplicates():
    async with AsyncSessionLocal() as session:
        print("🔍 Checking for duplicate customers...\n")
        
        # Check for duplicate telegram_user_id
        print("=" * 50)
        print("TELEGRAM USER ID DUPLICATES:")
        print("=" * 50)
        result = await session.execute(
            select(Customer.telegram_user_id, func.count(Customer.id))
            .where(Customer.telegram_user_id.isnot(None))
            .group_by(Customer.telegram_user_id)
            .having(func.count(Customer.id) > 1)
        )
        telegram_dups = result.all()
        
        if telegram_dups:
            for user_id, count in telegram_dups:
                print(f"\n❌ telegram_user_id={user_id} has {count} records:")
                customers = await session.execute(
                    select(Customer).where(Customer.telegram_user_id == user_id)
                )
                for cust in customers.scalars():
                    print(f"   - Customer ID: {cust.id}, Status: {cust.customer_status.value}, "
                          f"Name: {cust.first_name}, Bale ID: {cust.bale_user_id}")
        else:
            print("✅ No telegram_user_id duplicates found")
        
        # Check for duplicate bale_user_id
        print("\n" + "=" * 50)
        print("BALE USER ID DUPLICATES:")
        print("=" * 50)
        result = await session.execute(
            select(Customer.bale_user_id, func.count(Customer.id))
            .where(Customer.bale_user_id.isnot(None))
            .group_by(Customer.bale_user_id)
            .having(func.count(Customer.id) > 1)
        )
        bale_dups = result.all()
        
        if bale_dups:
            for user_id, count in bale_dups:
                print(f"\n❌ bale_user_id={user_id} has {count} records:")
                customers = await session.execute(
                    select(Customer).where(Customer.bale_user_id == user_id)
                )
                for cust in customers.scalars():
                    print(f"   - Customer ID: {cust.id}, Status: {cust.customer_status.value}, "
                          f"Name: {cust.first_name}, Telegram ID: {cust.telegram_user_id}")
        else:
            print("✅ No bale_user_id duplicates found")
        
        # Check for customers with BOTH telegram and bale
        print("\n" + "=" * 50)
        print("LINKED ACCOUNTS (Telegram + Bale):")
        print("=" * 50)
        result = await session.execute(
            select(Customer).where(
                Customer.telegram_user_id.isnot(None),
                Customer.bale_user_id.isnot(None)
            )
        )
        linked = result.scalars().all()
        
        if linked:
            for cust in linked:
                print(f"\n✅ Customer ID: {cust.id}")
                print(f"   Telegram: {cust.telegram_user_id} ({cust.telegram_first_name})")
                print(f"   Bale: {cust.bale_user_id} ({cust.bale_first_name})")
                print(f"   Status: {cust.customer_status.value}")
        else:
            print("ℹ️ No linked accounts found")

if __name__ == "__main__":
    asyncio.run(check_duplicates())
