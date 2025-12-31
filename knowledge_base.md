# Rajtech Technological Systems (RTS) - Knowledge Base

## About the Organization

Rajtech Technological Systems is a multi-tenant education management platform designed for franchise-based computer education institutions. The platform manages students, courses, staff, payments, examinations, certificates, and payroll across multiple institutions.

## System Roles & Access

### User Roles
1. **Super Admin (System Director)**
   - Full system access across all institutions
   - Can create and manage institutions
   - Oversees entire platform

2. **Institution Director**
   - Full access to their institution
   - Manages staff, students, courses
   - Sets staff daily rates
   - Approves enrollments

3. **Accountant**
   - Enter examination marks
   - View students and courses
   - Manage fee payments
   - Generate financial reports

4. **Receptionist**
   - Record fee payments only
   - Search students by ID
   - Generate payment receipts

5. **Staff Manager**
   - Manage staff and students
   - Mark attendance
   - Handle day-to-day operations

6. **Staff**
   - Mark attendance
   - View assigned students
   - Limited access

7. **Student**
   - View own profile and progress
   - Access course materials
   - View certificates and payments

## Student Registration & Enrollment

### How to Register a New Student

**Step-by-Step Process:**

1. **Login Required**: Staff Manager, Accountant, or Director must be logged in

2. **Navigate to Students Page**: Go to Dashboard → Students → "Register New Student" button

3. **Fill Student Information**:
   - Full Name (required)
   - Email Address (required - will be login username)
   - Phone Number (required)
   - Date of Birth (required)
   - Father's Name
   - Guardian Name (if different from father)
   - Guardian Phone
   - Complete Address
   - Aadhar Number (12 digits)
   - APAAR ID (if available)
   - Last Qualification (educational background)

4. **Batch Information**:
   - Batch Time (e.g., "9AM-10AM", "10AM-11AM", "3PM-4PM")
   - Batch Month (MM format, e.g., "01" for January)
   - Batch Year (YYYY format, e.g., "2025")
   - Batch Identifier ("A" or "B" for multiple batches in same month)

5. **Course Selection**: Choose the course to enroll in (optional during registration)

6. **Submit**: Click submit button

7. **Auto-Generated Details**:
   - Student ID is automatically generated in format: `RTS-DISTRICT-INST-MM-YYYY-NNNN`
   - Example: `RTS-NAL-RCC-12-2025-0001`
   - Default password is set to student's phone number

8. **Post-Registration**:
   - Student receives login credentials
   - Can login with email and phone number as password
   - Should change password after first login

### Student ID Format

**Format**: `RTS-DISTRICT-INST-MM-YYYY-NNNN`

**Components**:
- `RTS`: Platform prefix
- `DISTRICT`: District code (e.g., NAL for Nalanda, PAT for Patna)
- `INST`: Institution initials (first letter of each word)
- `MM`: Enrollment month (01-12)
- `YYYY`: Enrollment year
- `NNNN`: Sequential number (0001, 0002, etc.)

**Example**: `RTS-NAL-RCC-12-2025-0001`
- Rajtech Computer Center in Nalanda district
- Enrolled in December 2025
- First student of that month

## Available Courses

The platform supports multiple course types with modular structure:

### Course Types
1. **ADCA** - Advanced Diploma in Computer Application
   - Duration: 12-18 months
   - 13 modules, 363 lessons
   - Comprehensive computer training

2. **HDIT** - Hardware & IT Technician
   - Duration: 12 months
   - 11 modules, 308 lessons
   - Hardware and networking focus

3. **DCA** - Diploma in Computer Application
   - Duration: 6-12 months
   - 7 modules, 188 lessons
   - Basic computer skills

4. **DOARM** - Diploma in Office Automation & Records Management
   - Duration: 6-12 months
   - 7 modules, 147 lessons
   - Office productivity focus

### Course Features
- Structured modules with lessons
- Module-wise examinations
- Progress tracking
- Certificate upon completion
- Attendance monitoring
- Fee payment tracking

## Fee Payment System

### Recording a Payment

**Who Can Record**: Receptionist, Accountant, or Director

**Process**:
1. Navigate to Payments page
2. Search for student using Student ID (e.g., RTS-NAL-RCC-12-2025-0001)
3. Select the course for payment
4. Enter payment details:
   - Amount
   - Payment Method (cash, online, UPI, card, bank_transfer)
   - Transaction ID (required for online/UPI/card payments)
   - Notes (optional)
5. Submit payment
6. Receipt is auto-generated with unique receipt number

### Payment Methods
- **Cash**: Direct cash payment
- **Online**: Online payment gateway
- **UPI**: UPI payments (requires transaction ID)
- **Card**: Credit/Debit card (requires transaction ID)
- **Bank Transfer**: Direct bank transfer

### Receipt Format
- Receipt Number: `RCT-INST-YYYY-NNNN`
- Example: `RCT-RAJ-2025-0001`
- Downloadable PDF receipt available
- Shows: Student name, course, amount paid, balance, payment method

### Payment Summary
- View total fees for each course
- Track total paid amount
- See remaining balance
- Payment history with dates

## Examination System

### Exam Types
1. **Module Exams**: For each course module
2. **Internal Assessments**: Regular tests
3. **Final Exams**: End of course
4. **Practical Exams**: Hands-on assessments

### Exam Features
- **MCQ Format**: Multiple choice questions (A, B, C, D options)
- **Timed Exams**: Duration set per exam (typically 60 minutes)
- **Passing Marks**: Usually 40% minimum
- **Question Shuffling**: Random order for each student
- **Option Shuffling**: Randomized answer options
- **Batch-Specific**: Exams scheduled for specific batches

### Exam Process for Students
1. **Scheduled**: Exams are scheduled by administrators
2. **Notification**: Students receive notifications
3. **Take Exam**: Access through student dashboard
4. **Time Limit**: Must complete within duration
5. **Submit**: Submit answers before time expires
6. **Verification**: Results verified by staff
7. **View Results**: After verification, view marks and percentage

### Exam Scheduling
- Scheduled by date and time
- Targeted to specific batches (by time, month, year)
- Start time and end time defined
- Students can only take during scheduled window

### Marks Entry (Manual)
**Who Can Enter**: Accountant or Director

**Process**:
1. Go to Marks Entry page
2. Select course and module
3. Select student
4. Enter marks obtained
5. System auto-calculates pass/fail based on passing marks
6. Marks are recorded with date and entered by whom

### Exam Verification
- Results require verification before being visible to students
- Verification done by authorized staff
- Prevents cheating and ensures accuracy
- Verified results are final

## Certificate Generation

### Certificate Types
1. **Course Completion Certificate**: After completing all modules
2. **Module Certificates**: For individual module completion
3. **Merit Certificates**: For outstanding performance

### Certificate Requirements
- Complete all course modules
- Pass all module examinations (minimum 40%)
- Clear all fee payments (no pending dues)
- Maintain minimum 75% attendance (if applicable)

### Certificate Features
- Unique certificate number
- Student name and course details
- Issue date
- Digitally signed
- QR code for verification
- Downloadable PDF format

### How to Generate Certificate
**Who Can Generate**: Director or Accountant

**Process**:
1. Navigate to Certificates page
2. Select student
3. Select completed course
4. Click "Generate Certificate"
5. Certificate PDF is created
6. Student can download from their dashboard

## Staff Management

### Staff Roles
- Teachers/Instructors
- Administrators
- Accountants
- Receptionists
- Support Staff

### Staff Information
- Personal details
- Position/designation
- Daily rate (set by director)
- Joining date
- Contact information

### Daily Rate System
- Each staff member has a daily earning rate
- Set by Institution Director
- Used for payroll calculation
- Can be updated as needed

## Attendance System

### Staff Attendance
**Who Can Mark**: Staff Manager or Director

**Attendance Status**:
- **Present**: Full day attendance
- **Absent**: Not present
- **Half Day**: Partial attendance (50% pay)
- **Leave**: Approved leave

**Process**:
1. Go to Attendance page
2. Select date
3. Mark attendance for each staff member
4. Can mark in batch (multiple staff at once)
5. Add notes if needed
6. Submit attendance

### Attendance Summary
- Monthly attendance reports
- Total present days
- Total absent days
- Half days count
- Leave days
- Used for payroll calculation

## Payroll System

### Payroll Calculation
**Formula**:
```
Total Salary = (Present Days × Daily Rate) + (Half Days × Daily Rate × 0.5)
```

**Example**:
- Daily Rate: ₹500
- Present Days: 20
- Half Days: 2
- Calculation: (20 × 500) + (2 × 500 × 0.5) = ₹10,000 + ₹500 = ₹10,500

### Payroll Generation
**Who Can Generate**: Director or Accountant

**Process**:
1. Navigate to Payroll page
2. Select month and year
3. Click "Generate Payroll"
4. System calculates based on attendance
5. Review generated payroll
6. Approve and finalize

### Payslip Features
- Staff name and position
- Month and year
- Total working days
- Present days, absent days, half days
- Daily rate
- Gross salary
- Deductions (if any)
- Net salary
- Downloadable PDF payslip

## Institution Management

### Institution Details
- Institution name
- District code (for student ID generation)
- Address
- Contact email and phone
- Director assignment

### Multi-Tenant System
- Each institution has isolated data
- Users can only access their institution's data
- Super Admin can access all institutions
- Data security and privacy maintained

## Dashboard Features

### Analytics Dashboard
- Total students count
- Total staff count
- Revenue tracking
- Course enrollment statistics
- Attendance trends
- Payment collection status

### Revenue Tracking
- Total fees collected
- Pending payments
- Payment method breakdown
- Monthly revenue reports
- Course-wise revenue

## Technical Support

### Getting Help
- **In-App Chat**: Use the AI chatbot (Raj) in bottom-right corner
- **Email Support**: Contact your institution director
- **Documentation**: Refer to user guides in dashboard

### Common Issues

**Login Problems**:
- Use email as username
- Default password is phone number for new students
- Use "Forgot Password" if needed
- Contact institution admin if account is inactive

**Payment Issues**:
- Verify payment method selected correctly
- For online payments, transaction ID is mandatory
- Check payment history in student dashboard
- Contact receptionist or accountant for discrepancies

**Certificate Delays**:
- Ensure all modules are completed
- Verify all payments are cleared
- Check with accountant for pending marks entry
- Certificates generated within 7 days of completion

**Attendance Discrepancies**:
- Report to staff manager within 7 days
- Provide date and details
- Attendance can be corrected by authorized staff

## Security & Privacy

### Data Protection
- All personal data is encrypted
- Secure password storage (bcrypt hashing)
- JWT token-based authentication
- Session timeout for security
- Multi-tenant data isolation

### Account Security
- Strong password recommended
- Change default password after first login
- Logout from shared devices
- Report suspicious activity immediately

## Mobile Access

- Responsive web design works on all devices
- Access from smartphones and tablets
- Same features as desktop
- Optimized for mobile viewing
- No separate app needed

## Important Policies

### Attendance Policy (if applicable)
- Minimum attendance may be required for exam eligibility
- Varies by institution
- Check with your institution director

### Examination Policy
- Passing marks: 40% minimum (may vary by course)
- Retakes may be allowed (check with institution)
- Malpractice results in exam cancellation
- Results declared after verification

### Payment Policy
- Fees must be paid as per schedule
- Installment options may be available
- Late payment may incur penalties
- Refund policy varies by institution

## Batch System

### Batch Organization
Students are organized into batches based on:
- **Batch Time**: Class timing (e.g., "9AM-10AM", "3PM-4PM")
- **Batch Month**: Month of enrollment (MM format)
- **Batch Year**: Year of enrollment (YYYY format)
- **Batch Identifier**: "A" or "B" for multiple batches in same month

### Purpose
- Organize students by enrollment period
- Schedule batch-specific exams
- Track cohort progress
- Manage class timings

## Module Progress Tracking

### Progress Status
- **Not Started**: Module not yet begun
- **In Progress**: Currently studying
- **Completed**: Passed the module exam
- **Failed**: Did not pass (can retake)

### Viewing Progress
Students can view:
- Total modules in course
- Completed modules count
- In-progress modules
- Overall completion percentage
- Marks obtained in each module

## Contact Information

**Platform**: Rajtech Technological Systems
**Support**: Contact your institution director
**Technical Issues**: Use in-app chatbot or email support

---

*Last Updated: December 2024*
*This knowledge base covers the core features of the RTS platform. For institution-specific policies, contact your institution director.*