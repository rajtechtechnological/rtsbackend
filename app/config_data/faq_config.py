"""
FAQ Configuration for RTS Chatbot
Predefined questions and answers for common queries
"""

FAQ_DATABASE = [
    # Student Registration
    {
        "id": "reg_001",
        "category": "registration",
        "question": "How do I register as a student?",
        "variations": [
            "how to register",
            "student registration process",
            "how can i enroll",
            "registration steps",
            "how to become a student",
            "enrollment process",
            "sign up as student"
        ],
        "answer": """To register as a new student:

1. Contact your institution (staff manager, accountant, or director must register you)
2. They will need your information:
   - Full Name, Email, Phone Number
   - Date of Birth, Address
   - Father's/Guardian Name and Phone
   - Aadhar Number, Last Qualification
   - Batch details (time, month, year)

3. You'll receive:
   - Student ID (format: RTS-DISTRICT-INST-MM-YYYY-NNNN)
   - Login credentials (email and phone as password)

4. Login and change your password

Note: Students cannot self-register. Contact your institution for enrollment."""
    },
    {
        "id": "reg_002",
        "question": "What is my student ID format?",
        "variations": [
            "student id format",
            "how is student id generated",
            "student id structure",
            "what does student id mean"
        ],
        "answer": """Student ID Format: RTS-DISTRICT-INST-MM-YYYY-NNNN

Example: RTS-NAL-RCC-12-2025-0001

Components:
- RTS: Platform prefix
- DISTRICT: District code (e.g., NAL for Nalanda)
- INST: Institution initials (e.g., RCC for Rajtech Computer Center)
- MM: Enrollment month (01-12)
- YYYY: Enrollment year
- NNNN: Sequential number (0001, 0002, etc.)

This ID is automatically generated during registration."""
    },

    # Courses
    {
        "id": "course_001",
        "category": "courses",
        "question": "What courses are available?",
        "variations": [
            "available courses",
            "course list",
            "what can i study",
            "course options",
            "which courses offered"
        ],
        "answer": """Available Courses:

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

Each course includes structured modules, examinations, and certificate upon completion."""
    },

    # Payments
    {
        "id": "pay_001",
        "category": "payments",
        "question": "How do I pay my fees?",
        "variations": [
            "fee payment",
            "how to pay fees",
            "payment process",
            "pay course fees",
            "make payment"
        ],
        "answer": """To pay your fees:

1. Visit your institution's office
2. Provide your Student ID to receptionist/accountant
3. Choose payment method:
   - Cash
   - Online payment
   - UPI (requires transaction ID)
   - Card (requires transaction ID)
   - Bank Transfer

4. Receive payment receipt with unique receipt number
5. Download PDF receipt from your dashboard

Payment Methods:
- Cash: Direct payment at office
- Online/UPI/Card: Transaction ID required
- Bank Transfer: Provide transfer details

You can view payment history and balance in your student dashboard."""
    },
    {
        "id": "pay_002",
        "question": "Where can I see my payment history?",
        "variations": [
            "payment history",
            "view payments",
            "check payment status",
            "payment records",
            "fee balance"
        ],
        "answer": """To view your payment history:

1. Login to your student dashboard
2. Navigate to "Payments" section
3. You'll see:
   - All payment records with dates
   - Receipt numbers
   - Payment methods used
   - Total fees for each course
   - Amount paid
   - Remaining balance

You can also download PDF receipts for each payment from this section."""
    },

    # Examinations
    {
        "id": "exam_001",
        "category": "exams",
        "question": "How do exams work?",
        "variations": [
            "examination process",
            "how to take exam",
            "exam system",
            "online exam",
            "test process"
        ],
        "answer": """Examination System:

**Exam Types:**
- Module exams for each course module
- Internal assessments
- Final exams
- Practical exams

**Process:**
1. Exams are scheduled by administrators for your batch
2. You receive notification of exam schedule
3. Access exam through student dashboard during scheduled time
4. Complete MCQ questions within time limit (usually 60 minutes)
5. Submit before time expires
6. Results are verified by staff
7. View marks after verification

**Features:**
- Multiple choice questions (A, B, C, D)
- Questions and options are shuffled
- Timed exams
- Passing marks: 40% minimum
- Results require staff verification

Check your dashboard for upcoming scheduled exams."""
    },
    {
        "id": "exam_002",
        "question": "What is the passing marks?",
        "variations": [
            "passing percentage",
            "minimum marks to pass",
            "pass marks",
            "passing criteria"
        ],
        "answer": """Passing Marks: **40% minimum**

This means:
- If total marks = 100, you need 40 marks to pass
- If total marks = 50, you need 20 marks to pass

**Important:**
- Passing marks may vary slightly by course/module
- Check specific module requirements
- Results are verified by staff before being final
- Failed modules can typically be retaken (check with institution)

Your marks and pass/fail status will be visible in your dashboard after staff verification."""
    },

    # Certificates
    {
        "id": "cert_001",
        "category": "certificates",
        "question": "How do I get my certificate?",
        "variations": [
            "certificate generation",
            "get certificate",
            "download certificate",
            "course completion certificate",
            "when will i get certificate"
        ],
        "answer": """To get your certificate:

**Requirements:**
1. Complete all course modules
2. Pass all module examinations (minimum 40%)
3. Clear all fee payments (no pending dues)
4. Maintain required attendance (if applicable)

**Process:**
1. After meeting all requirements, certificate is generated by director/accountant
2. You'll receive notification
3. Download PDF certificate from your dashboard
4. Certificate includes:
   - Unique certificate number
   - Your name and course details
   - Issue date
   - QR code for verification

**Timeline:**
Certificates are typically generated within 7 days of course completion.

If delayed, contact your institution's accountant or director."""
    },

    # Attendance
    {
        "id": "attend_001",
        "category": "attendance",
        "question": "How is attendance tracked?",
        "variations": [
            "attendance system",
            "view attendance",
            "check attendance",
            "attendance record"
        ],
        "answer": """Attendance Tracking:

**For Students:**
- Attendance is marked by staff/teachers
- View your attendance records in dashboard
- Check attendance percentage
- May receive alerts for low attendance

**Attendance Status:**
- Present: Full attendance
- Absent: Not present
- Half Day: Partial attendance
- Leave: Approved leave

**Important:**
- Some courses may require minimum attendance for exam eligibility
- Report discrepancies to staff manager within 7 days
- Attendance policy varies by institution

Check your student dashboard for detailed attendance records."""
    },

    # Login & Access
    {
        "id": "login_001",
        "category": "login",
        "question": "I forgot my password, what should I do?",
        "variations": [
            "forgot password",
            "reset password",
            "can't login",
            "password recovery",
            "login problem"
        ],
        "answer": """If you forgot your password:

1. **Default Password:** For new students, default password is your phone number
2. **Use Forgot Password:** Click "Forgot Password" on login page (if available)
3. **Contact Institution:** Contact your institution's admin/director to reset password

**Login Credentials:**
- Username: Your email address
- Password: Phone number (default) or your changed password

**Security Tips:**
- Change default password after first login
- Use strong password
- Don't share credentials
- Logout from shared devices

If account is inactive, contact your institution director."""
    },
    {
        "id": "login_002",
        "question": "What are my login credentials?",
        "variations": [
            "login details",
            "username password",
            "how to login",
            "login credentials",
            "sign in details"
        ],
        "answer": """Your Login Credentials:

**Username:** Your email address (provided during registration)

**Password:** 
- Default: Your phone number
- Change after first login for security

**Login Process:**
1. Go to login page
2. Enter email as username
3. Enter password (phone number if first time)
4. Click login
5. Change password in profile settings

**Troubleshooting:**
- Ensure email is correct
- Try phone number as password
- Check if account is active
- Contact institution if issues persist

Access the platform at your institution's provided URL."""
    },

    # Dashboard & Features
    {
        "id": "dash_001",
        "category": "dashboard",
        "question": "What can I see in my dashboard?",
        "variations": [
            "dashboard features",
            "student dashboard",
            "what's in dashboard",
            "dashboard access"
        ],
        "answer": """Student Dashboard Features:

**Overview:**
- Your profile information
- Enrolled courses
- Overall progress

**Courses:**
- View enrolled courses
- Module-wise progress
- Completion percentage
- Marks obtained

**Payments:**
- Payment history
- Pending fees
- Download receipts
- Balance information

**Exams:**
- Scheduled exams
- Take online exams
- View results
- Exam history

**Certificates:**
- Download certificates
- View certificate details
- Verification QR codes

**Profile:**
- Update personal information
- Change password
- View student ID

Navigate through the menu to access different sections."""
    },

    # Roles & Access
    {
        "id": "role_001",
        "category": "roles",
        "question": "What are the different user roles?",
        "variations": [
            "user roles",
            "types of users",
            "who can do what",
            "role permissions"
        ],
        "answer": """User Roles in RTS:

1. **Super Admin (System Director)**
   - Full system access
   - Manages all institutions

2. **Institution Director**
   - Full access to their institution
   - Manages staff and students
   - Sets staff rates

3. **Accountant**
   - Enter marks
   - Manage payments
   - Generate reports

4. **Receptionist**
   - Record payments only
   - Generate receipts

5. **Staff Manager**
   - Manage students and staff
   - Mark attendance
   - Daily operations

6. **Staff**
   - Mark attendance
   - View students
   - Limited access

7. **Student**
   - View own data
   - Take exams
   - Access materials

Each role has specific permissions for data security."""
    },

    # Technical Support
    {
        "id": "support_001",
        "category": "support",
        "question": "How do I get help or support?",
        "variations": [
            "get help",
            "contact support",
            "technical support",
            "need assistance",
            "help desk"
        ],
        "answer": """Getting Help:

**In-App Support:**
- Use this AI chatbot (Raj) for instant answers
- Available 24/7 in bottom-right corner

**Institution Support:**
- Contact your institution director
- Reach out to accountant for payment issues
- Contact staff manager for general queries

**Common Issues:**
- Login problems: Try phone number as password
- Payment issues: Contact receptionist/accountant
- Certificate delays: Contact accountant
- Attendance issues: Report to staff manager within 7 days

**Technical Issues:**
- Clear browser cache
- Try different browser
- Check internet connection
- Contact institution admin

For urgent matters, visit your institution office directly."""
    },

    # Progress Tracking
    {
        "id": "progress_001",
        "category": "progress",
        "question": "How can I track my course progress?",
        "variations": [
            "view progress",
            "course progress",
            "track learning",
            "completion status",
            "module progress"
        ],
        "answer": """Tracking Your Progress:

**In Student Dashboard:**
1. Go to "Courses" section
2. Select your enrolled course
3. View module-wise progress

**Progress Information:**
- Total modules in course
- Completed modules
- In-progress modules
- Not started modules
- Overall completion percentage
- Marks obtained in each module

**Module Status:**
- **Not Started:** Module not yet begun
- **In Progress:** Currently studying
- **Completed:** Passed the module exam
- **Failed:** Did not pass (can retake)

**Marks Display:**
- Marks obtained / Total marks
- Percentage
- Pass/Fail status
- Exam date

Your progress is updated after each module exam is verified by staff."""
    }
]

def get_all_faqs():
    """Return all FAQs"""
    return FAQ_DATABASE

def get_faq_by_id(faq_id: str):
    """Get specific FAQ by ID"""
    for faq in FAQ_DATABASE:
        if faq["id"] == faq_id:
            return faq
    return None

def get_faqs_by_category(category: str):
    """Get all FAQs in a category"""
    return [faq for faq in FAQ_DATABASE if faq.get("category") == category]

def search_faq(query: str, threshold: float = 0.3):
    """
    Search FAQ using simple text matching
    Returns list of matching FAQs with confidence scores
    """
    query_lower = query.lower()
    results = []
    
    for faq in FAQ_DATABASE:
        score = 0.0
        
        # Check main question
        if query_lower in faq["question"].lower():
            score += 1.0
        
        # Check variations
        for variation in faq.get("variations", []):
            if query_lower in variation.lower() or variation.lower() in query_lower:
                score += 0.8
                break
        
        # Word matching
        query_words = set(query_lower.split())
        question_words = set(faq["question"].lower().split())
        variation_words = set()
        for v in faq.get("variations", []):
            variation_words.update(v.lower().split())
        
        all_words = question_words.union(variation_words)
        common_words = query_words.intersection(all_words)
        
        if len(query_words) > 0:
            word_score = len(common_words) / len(query_words)
            score += word_score * 0.5
        
        if score >= threshold:
            results.append({
                "faq": faq,
                "confidence": min(score, 1.0)
            })
    
    # Sort by confidence
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results

# Made with Bob
