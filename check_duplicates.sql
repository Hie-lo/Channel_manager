-- SQL queries to check for duplicate customer records
-- Run these directly in your PostgreSQL database

-- ===================================================================
-- 1. Check for duplicate telegram_user_id
-- ===================================================================
SELECT 
    telegram_user_id, 
    COUNT(*) as count,
    STRING_AGG(CAST(id AS TEXT), ', ') as customer_ids,
    STRING_AGG(COALESCE(first_name, '?'), ', ') as names,
    STRING_AGG(CAST(customer_status AS TEXT), ', ') as statuses
FROM customers 
WHERE telegram_user_id IS NOT NULL
GROUP BY telegram_user_id 
HAVING COUNT(*) > 1;

-- ===================================================================
-- 2. Check for duplicate bale_user_id
-- ===================================================================
SELECT 
    bale_user_id, 
    COUNT(*) as count,
    STRING_AGG(CAST(id AS TEXT), ', ') as customer_ids,
    STRING_AGG(COALESCE(first_name, '?'), ', ') as names,
    STRING_AGG(CAST(customer_status AS TEXT), ', ') as statuses
FROM customers 
WHERE bale_user_id IS NOT NULL
GROUP BY bale_user_id 
HAVING COUNT(*) > 1;

-- ===================================================================
-- 3. Show all customers with BOTH telegram and bale linked
-- ===================================================================
SELECT 
    id,
    telegram_user_id,
    telegram_first_name,
    bale_user_id,
    bale_first_name,
    customer_status,
    created_at
FROM customers 
WHERE telegram_user_id IS NOT NULL 
  AND bale_user_id IS NOT NULL
ORDER BY created_at DESC;

-- ===================================================================
-- 4. Check for the specific user from the error (ID: 6958666033)
-- ===================================================================
SELECT 
    id,
    telegram_user_id,
    telegram_first_name,
    telegram_username,
    bale_user_id,
    bale_first_name,
    bale_username,
    customer_status,
    created_at
FROM customers 
WHERE telegram_user_id = 6958666033 
   OR bale_user_id = 6958666033
   OR telegram_first_name LIKE '%Darci%'
   OR bale_first_name LIKE '%Darci%';

-- ===================================================================
-- 5. Show all PENDING customers (might be temp accounts)
-- ===================================================================
SELECT 
    id,
    telegram_user_id,
    bale_user_id,
    first_name,
    customer_status,
    created_at
FROM customers 
WHERE customer_status = 'PENDING'
ORDER BY created_at DESC;
