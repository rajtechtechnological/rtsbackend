# Demo Data - Login Credentials

All demo users have been created successfully! Use these credentials to test the system.

## 📧 Login Credentials

### 1. Super Admin (System Director)
- **Email:** director@rajtech.com
- **Password:** director123
- **Role:** super_admin
- **Access:** Full system access, manages all institutions

### 2. Institution Director
- **Email:** director.demo@rajtech.com
- **Password:** director123
- **Role:** institution_director
- **Institution:** Demo Raj Technical Institute
- **Access:** Full access to their institution

### 3. Accountant
- **Email:** accountant@rajtech.com
- **Password:** accountant123
- **Role:** accountant
- **Access:** Enter marks, view students, manage fees

### 4. Receptionist
- **Email:** receptionist@rajtech.com
- **Password:** receptionist123
- **Role:** receptionist
- **Access:** Record payments only

### 5. Staff Manager
- **Email:** manager@rajtech.com
- **Password:** manager123
- **Role:** staff_manager
- **Access:** Manage staff, students, and operations

### 6. Regular Staff
- **Email:** staff@rajtech.com
- **Password:** staff123
- **Role:** staff
- **Access:** Mark attendance, view students

### 7. Student
- **Email:** student@rajtech.com
- **Password:** student123
- **Role:** student
- **Student ID:** RTS-DEMO-12-2025-0001
- **Enrolled In:** ADCA (Advanced Diploma in Computer Application)
- **Status:** Active, with 13 modules initialized

---

## 🏢 Demo Institution
- **Name:** Demo Raj Technical Institute
- **District Code:** DEMO
- **Address:** 123 Demo Street, Test City, 123456

---

## 📚 Available Courses
The following courses have been populated with modules:
1. **ADCA** - Advanced Diploma in Computer Application (13 modules, 363 lessons)
2. **HDIT** - Hardware & IT Technician (11 modules, 308 lessons)
3. **DCA** - Diploma in Computer Application (7 modules, 188 lessons)
4. **DOARM** - Diploma in Office Automation & Records Management (7 modules, 147 lessons)

---

## ⚠️ IMPORTANT SECURITY NOTE
**These are demo credentials for testing only!**
- Change all passwords after first login in production
- Never commit this file to version control
- Use strong, unique passwords for production deployments

---

## 🧪 Testing Scenarios

### Test Student Progress Tracking
1. Login as **student@rajtech.com**
2. View enrolled courses and module progress
3. See status of all 13 ADCA modules

### Test Marks Entry
1. Login as **accountant@rajtech.com**
2. Go to Marks Entry page
3. Select ADCA course and any module
4. Enter marks for the demo student
5. Verify pass/fail calculation

### Test Payment Recording
1. Login as **receptionist@rajtech.com**
2. Go to Payments page
3. Search for student: RTS-DEMO-12-2025-0001
4. Record a fee payment

### Test Staff Management
1. Login as **director.demo@rajtech.com** or **manager@rajtech.com**
2. View staff list
3. Add attendance records
4. Generate payroll

---

## 🔄 Reset Demo Data

To recreate demo data from scratch:
```bash
cd rtsbackend
python create_demo_data.py
```

The script is idempotent - it won't create duplicates if users already exist.

