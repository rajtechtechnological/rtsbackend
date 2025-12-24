-- SQL script to create a fixed director account
-- Run this script in your PostgreSQL database after tables are created

-- Insert the director user
-- Password: director123 (hashed with bcrypt)
INSERT INTO users (id, email, hashed_password, full_name, phone, role, institution_id, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'director@rajtech.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/JQwJ3x.vW9qQ6TqXC',  -- Password: director123
    'System Director',
    '+91 9876543210',
    'super_admin',
    NULL,  -- Director has no institution (manages all)
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING;

-- Display success message
SELECT 'Director account created successfully!' as message,
       'Email: director@rajtech.com' as email,
       'Password: director123' as password;
