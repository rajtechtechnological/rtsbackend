-- Insert Diploma in Computer Application (DCA)
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'Diploma in Computer Application (DCA)',
    'Fundamentals of Computer, MS Windows, MS Office (Word, Excel, Access, PowerPoint). Complete office automation package for beginners.',
    6,
    3600.00,
    NOW()
);

-- Insert Advanced Diploma in Computer Application (ADCA)
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'Advanced Diploma in Computer Application (ADCA)',
    'DCA + DTP + Tally. Complete package for computer proficiency with accounting skills.',
    12,
    10000.00,
    NOW()
);

-- Insert Tally Prime with GST
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'Tally Prime with GST',
    'Financial Accounting with Tally latest version including Inventory, VAT, TDS, TCS, GST, and Payroll management.',
    3,
    3000.00,
    NOW()
);

-- Insert Diploma in Financial Accounting (DFA)
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'Diploma in Financial Accounting (DFA)',
    'DCA + CFA combination. Complete computerized accounting course with practical training.',
    9,
    5500.00,
    NOW()
);

-- Insert Post Graduate Diploma in Computer Application (PGDCA)
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'PGDCA',
    'Post Graduate Diploma in Computer Application - Fundamentals, MS-Office, DBMS, Visual Basic, C++, and advanced computer concepts.',
    18,
    NULL,
    NOW()
);

-- Insert Computer Typing (Hindi & English)
INSERT INTO courses (id, institution_id, name, description, duration_months, fee_amount, created_at)
VALUES (
    gen_random_uuid(),
    NULL,
    'Computer Typing (Hindi & English)',
    'Professional typing course covering basic typing, lessons, letters, words, and paragraph typing in both Hindi and English.',
    3,
    2200.00,
    NOW()
);
