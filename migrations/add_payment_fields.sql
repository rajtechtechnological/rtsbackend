-- Migration: Add new payment fields to fee_payments table
-- Date: 2025-12-29

-- Add payment_method column
ALTER TABLE fee_payments
ADD COLUMN IF NOT EXISTS payment_method VARCHAR;

-- Add transaction_id column
ALTER TABLE fee_payments
ADD COLUMN IF NOT EXISTS transaction_id VARCHAR;

-- Add receipt_number column (unique)
ALTER TABLE fee_payments
ADD COLUMN IF NOT EXISTS receipt_number VARCHAR UNIQUE;

-- Add notes column
ALTER TABLE fee_payments
ADD COLUMN IF NOT EXISTS notes VARCHAR;

-- Add created_by column (foreign key to users table)
ALTER TABLE fee_payments
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_fee_payments_receipt_number ON fee_payments(receipt_number);
CREATE INDEX IF NOT EXISTS idx_fee_payments_payment_method ON fee_payments(payment_method);

-- Update existing records to have default payment_method (if any exist)
UPDATE fee_payments
SET payment_method = 'offline'
WHERE payment_method IS NULL;

-- Make payment_method NOT NULL after setting defaults
ALTER TABLE fee_payments
ALTER COLUMN payment_method SET NOT NULL;

-- Verify the changes
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'fee_payments'
ORDER BY ordinal_position;
