-- ⚠️⚠️⚠️ DANGER: COMPLETE DATABASE RESET ⚠️⚠️⚠️
-- This will delete ALL data from ALL tables
-- Use only if you're okay losing everything!

-- ===================================================================
-- BACKUP FIRST! Run this before resetting:
-- ===================================================================
-- pg_dump -U your_user -d your_db > backup_full.sql

-- ===================================================================
-- Delete all data in order (respecting foreign keys)
-- ===================================================================

-- Delete dependent data first
DELETE FROM ai_usage_logs;
DELETE FROM ai_token_packages;
DELETE FROM posted_messages;
DELETE FROM product_media;
DELETE FROM products;
DELETE FROM channels;
DELETE FROM subscriptions;
DELETE FROM account_link_codes;
DELETE FROM businesses;
DELETE FROM sheet_connections;
DELETE FROM post_template_presets;
DELETE FROM tutorials;
DELETE FROM customers;

-- ===================================================================
-- Reset auto-increment sequences
-- ===================================================================
ALTER SEQUENCE customers_id_seq RESTART WITH 1;
ALTER SEQUENCE channels_id_seq RESTART WITH 1;
ALTER SEQUENCE products_id_seq RESTART WITH 1;
ALTER SEQUENCE product_media_id_seq RESTART WITH 1;
ALTER SEQUENCE posted_messages_id_seq RESTART WITH 1;
ALTER SEQUENCE subscriptions_id_seq RESTART WITH 1;
ALTER SEQUENCE businesses_id_seq RESTART WITH 1;
ALTER SEQUENCE ai_token_packages_id_seq RESTART WITH 1;
ALTER SEQUENCE ai_usage_logs_id_seq RESTART WITH 1;
ALTER SEQUENCE account_link_codes_id_seq RESTART WITH 1;
ALTER SEQUENCE sheet_connections_id_seq RESTART WITH 1;
ALTER SEQUENCE post_template_presets_id_seq RESTART WITH 1;
ALTER SEQUENCE tutorials_id_seq RESTART WITH 1;

-- ===================================================================
-- Verify reset
-- ===================================================================
SELECT 
    'customers' as table_name, COUNT(*) as count FROM customers
UNION ALL SELECT 'channels', COUNT(*) FROM channels
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'posted_messages', COUNT(*) FROM posted_messages
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'businesses', COUNT(*) FROM businesses;

-- All counts should be 0
