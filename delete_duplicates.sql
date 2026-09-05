-- SQL script to delete duplicate/corrupted customer records
-- This will keep the oldest record and delete newer duplicates

-- ===================================================================
-- BACKUP FIRST! Run this before deleting anything:
-- ===================================================================
-- pg_dump -U your_user -d your_db > backup_before_cleanup.sql

-- ===================================================================
-- 1. Delete the specific corrupted user (ID: 6958666033)
-- ===================================================================
-- First, let's see what we have:
SELECT 
    id,
    telegram_user_id,
    bale_user_id,
    first_name,
    customer_status,
    created_at
FROM customers 
WHERE telegram_user_id = 6958666033 
   OR bale_user_id = 6958666033
ORDER BY created_at ASC;

-- To delete ALL records for this user (uncomment after reviewing):
-- DELETE FROM customers 
-- WHERE telegram_user_id = 6958666033 
--    OR bale_user_id = 6958666033;

-- ===================================================================
-- 2. Clean up ALL duplicate telegram_user_id (keep oldest)
-- ===================================================================
-- This finds duplicates and deletes newer ones, keeping the oldest:
DELETE FROM customers
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY telegram_user_id ORDER BY created_at ASC) as rn
        FROM customers
        WHERE telegram_user_id IS NOT NULL
    ) t
    WHERE rn > 1
);

-- ===================================================================
-- 3. Clean up ALL duplicate bale_user_id (keep oldest)
-- ===================================================================
DELETE FROM customers
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY bale_user_id ORDER BY created_at ASC) as rn
        FROM customers
        WHERE bale_user_id IS NOT NULL
    ) t
    WHERE rn > 1
);

-- ===================================================================
-- 4. Clean up orphaned PENDING customers (older than 1 day)
-- ===================================================================
DELETE FROM customers
WHERE customer_status = 'PENDING'
  AND created_at < NOW() - INTERVAL '1 day';

-- ===================================================================
-- 5. Verify cleanup
-- ===================================================================
SELECT 
    'Total customers' as check_type,
    COUNT(*) as count
FROM customers
UNION ALL
SELECT 
    'Active customers',
    COUNT(*)
FROM customers
WHERE customer_status = 'ACTIVE'
UNION ALL
SELECT 
    'Pending customers',
    COUNT(*)
FROM customers
WHERE customer_status = 'PENDING'
UNION ALL
SELECT 
    'Linked accounts (Telegram + Bale)',
    COUNT(*)
FROM customers
WHERE telegram_user_id IS NOT NULL 
  AND bale_user_id IS NOT NULL;
