"""
FAQ Configuration for RTS Chatbot
Predefined questions and answers for common queries — English and Hindi.
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

Note: Students cannot self-register. Contact your institution for enrollment.""",
        "answer_hi": """नए छात्र के रूप में पंजीकरण करने के लिए:

1. अपनी संस्था से संपर्क करें (स्टाफ मैनेजर, अकाउंटेंट या निदेशक आपको पंजीकृत करेंगे)
2. उन्हें आपकी निम्नलिखित जानकारी चाहिए होगी:
   - पूरा नाम, ईमेल, फ़ोन नंबर
   - जन्म तिथि, पता
   - पिता/अभिभावक का नाम और फ़ोन
   - आधार नंबर, अंतिम योग्यता
   - बैच विवरण (समय, माह, वर्ष)

3. आपको प्राप्त होगा:
   - छात्र ID (प्रारूप: RTS-DISTRICT-INST-MM-YYYY-NNNN)
   - लॉगिन क्रेडेंशियल (ईमेल और फ़ोन नंबर पासवर्ड के रूप में)

4. लॉगिन करें और अपना पासवर्ड बदलें

नोट: छात्र स्वयं पंजीकरण नहीं कर सकते। नामांकन के लिए अपनी संस्था से संपर्क करें।"""
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

This ID is automatically generated during registration.""",
        "answer_hi": """छात्र ID प्रारूप: RTS-DISTRICT-INST-MM-YYYY-NNNN

उदाहरण: RTS-NAL-RCC-12-2025-0001

घटक:
- RTS: प्लेटफ़ॉर्म उपसर्ग
- DISTRICT: जिला कोड (जैसे NAL नालंदा के लिए)
- INST: संस्था के आद्याक्षर (जैसे RCC राजटेक कंप्यूटर सेंटर के लिए)
- MM: नामांकन माह (01-12)
- YYYY: नामांकन वर्ष
- NNNN: क्रमांक (0001, 0002, आदि)

यह ID पंजीकरण के दौरान स्वचालित रूप से बनाई जाती है।"""
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

Each course includes structured modules, examinations, and certificate upon completion.""",
        "answer_hi": """उपलब्ध कोर्स:

1. **ADCA** - कंप्यूटर एप्लीकेशन में एडवांस्ड डिप्लोमा
   - अवधि: 12-18 माह
   - 13 मॉड्यूल, 363 पाठ
   - व्यापक कंप्यूटर प्रशिक्षण

2. **HDIT** - हार्डवेयर और IT तकनीशियन
   - अवधि: 12 माह
   - 11 मॉड्यूल, 308 पाठ
   - हार्डवेयर और नेटवर्किंग फ़ोकस

3. **DCA** - कंप्यूटर एप्लीकेशन में डिप्लोमा
   - अवधि: 6-12 माह
   - 7 मॉड्यूल, 188 पाठ
   - बुनियादी कंप्यूटर कौशल

4. **DOARM** - ऑफिस ऑटोमेशन और रिकॉर्ड मैनेजमेंट में डिप्लोमा
   - अवधि: 6-12 माह
   - 7 मॉड्यूल, 147 पाठ
   - कार्यालय उत्पादकता फ़ोकस

प्रत्येक कोर्स में संरचित मॉड्यूल, परीक्षाएं और पूर्णता पर प्रमाण पत्र शामिल हैं।"""
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

You can view payment history and balance in your student dashboard.""",
        "answer_hi": """फ़ीस भुगतान करने के लिए:

1. अपनी संस्था के कार्यालय में जाएं
2. रिसेप्शनिस्ट/अकाउंटेंट को अपना छात्र ID दें
3. भुगतान विधि चुनें:
   - नकद
   - ऑनलाइन भुगतान
   - UPI (ट्रांज़ेक्शन ID आवश्यक)
   - कार्ड (ट्रांज़ेक्शन ID आवश्यक)
   - बैंक ट्रांसफर

4. अनोखे रसीद नंबर के साथ भुगतान रसीद प्राप्त करें
5. अपने डैशबोर्ड से PDF रसीद डाउनलोड करें

भुगतान विधियां:
- नकद: कार्यालय में सीधा भुगतान
- ऑनलाइन/UPI/कार्ड: ट्रांज़ेक्शन ID आवश्यक
- बैंक ट्रांसफर: ट्रांसफर विवरण प्रदान करें

आप अपने छात्र डैशबोर्ड में भुगतान इतिहास और बैलेंस देख सकते हैं।"""
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

You can also download PDF receipts for each payment from this section.""",
        "answer_hi": """अपना भुगतान इतिहास देखने के लिए:

1. अपने छात्र डैशबोर्ड में लॉगिन करें
2. "Payments" अनुभाग पर जाएं
3. आप देखेंगे:
   - तारीखों के साथ सभी भुगतान रिकॉर्ड
   - रसीद नंबर
   - उपयोग की गई भुगतान विधियां
   - प्रत्येक कोर्स के लिए कुल फ़ीस
   - भुगतान की गई राशि
   - शेष बैलेंस

आप इस अनुभाग से प्रत्येक भुगतान की PDF रसीद भी डाउनलोड कर सकते हैं।"""
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

Check your dashboard for upcoming scheduled exams.""",
        "answer_hi": """परीक्षा प्रणाली:

**परीक्षा के प्रकार:**
- प्रत्येक कोर्स मॉड्यूल के लिए मॉड्यूल परीक्षाएं
- आंतरिक मूल्यांकन
- अंतिम परीक्षाएं
- प्रायोगिक परीक्षाएं

**प्रक्रिया:**
1. प्रशासकों द्वारा आपके बैच के लिए परीक्षाएं निर्धारित की जाती हैं
2. आपको परीक्षा कार्यक्रम की सूचना मिलती है
3. निर्धारित समय के दौरान छात्र डैशबोर्ड से परीक्षा में प्रवेश करें
4. समय सीमा के भीतर MCQ प्रश्न पूरे करें (आमतौर पर 60 मिनट)
5. समय समाप्त होने से पहले सबमिट करें
6. परिणाम स्टाफ द्वारा सत्यापित किए जाते हैं
7. सत्यापन के बाद अंक देखें

**विशेषताएं:**
- बहुविकल्पीय प्रश्न (A, B, C, D)
- प्रश्न और विकल्प फेरबदल किए जाते हैं
- समयबद्ध परीक्षाएं
- उत्तीर्ण अंक: न्यूनतम 40%
- परिणामों के लिए स्टाफ सत्यापन आवश्यक

आगामी निर्धारित परीक्षाओं के लिए अपना डैशबोर्ड देखें।"""
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

Your marks and pass/fail status will be visible in your dashboard after staff verification.""",
        "answer_hi": """उत्तीर्ण अंक: **न्यूनतम 40%**

इसका अर्थ है:
- यदि कुल अंक = 100, तो उत्तीर्ण होने के लिए 40 अंक चाहिए
- यदि कुल अंक = 50, तो उत्तीर्ण होने के लिए 20 अंक चाहिए

**महत्वपूर्ण:**
- उत्तीर्ण अंक कोर्स/मॉड्यूल के अनुसार थोड़ा भिन्न हो सकते हैं
- विशिष्ट मॉड्यूल आवश्यकताएं जांचें
- परिणाम अंतिम होने से पहले स्टाफ द्वारा सत्यापित किए जाते हैं
- असफल मॉड्यूल आमतौर पर दोबारा लिए जा सकते हैं (संस्था से जांचें)

स्टाफ सत्यापन के बाद आपके अंक और उत्तीर्ण/अनुत्तीर्ण स्थिति आपके डैशबोर्ड में दिखाई देगी।"""
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

If delayed, contact your institution's accountant or director.""",
        "answer_hi": """अपना प्रमाण पत्र पाने के लिए:

**आवश्यकताएं:**
1. सभी कोर्स मॉड्यूल पूरे करें
2. सभी मॉड्यूल परीक्षाएं उत्तीर्ण करें (न्यूनतम 40%)
3. सभी फ़ीस भुगतान पूरा करें (कोई बकाया नहीं)
4. आवश्यक उपस्थिति बनाए रखें (यदि लागू हो)

**प्रक्रिया:**
1. सभी आवश्यकताएं पूरी होने के बाद, निदेशक/अकाउंटेंट द्वारा प्रमाण पत्र बनाया जाता है
2. आपको सूचना मिलेगी
3. अपने डैशबोर्ड से PDF प्रमाण पत्र डाउनलोड करें
4. प्रमाण पत्र में शामिल है:
   - अनोखा प्रमाण पत्र नंबर
   - आपका नाम और कोर्स विवरण
   - जारी तिथि
   - सत्यापन के लिए QR कोड

**समय-सीमा:**
प्रमाण पत्र आमतौर पर कोर्स पूरा होने के 7 दिनों के भीतर बनाया जाता है।

यदि देरी हो, तो अपनी संस्था के अकाउंटेंट या निदेशक से संपर्क करें।"""
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

Check your student dashboard for detailed attendance records.""",
        "answer_hi": """उपस्थिति ट्रैकिंग:

**छात्रों के लिए:**
- उपस्थिति स्टाफ/शिक्षकों द्वारा दर्ज की जाती है
- डैशबोर्ड में अपने उपस्थिति रिकॉर्ड देखें
- उपस्थिति प्रतिशत जांचें
- कम उपस्थिति के लिए अलर्ट मिल सकते हैं

**उपस्थिति स्थिति:**
- उपस्थित: पूर्ण उपस्थिति
- अनुपस्थित: उपस्थित नहीं
- अर्ध दिवस: आंशिक उपस्थिति
- अवकाश: स्वीकृत छुट्टी

**महत्वपूर्ण:**
- कुछ कोर्स में परीक्षा पात्रता के लिए न्यूनतम उपस्थिति आवश्यक हो सकती है
- 7 दिनों के भीतर स्टाफ मैनेजर को विसंगतियों की रिपोर्ट करें
- उपस्थिति नीति संस्था के अनुसार भिन्न होती है

विस्तृत उपस्थिति रिकॉर्ड के लिए अपना छात्र डैशबोर्ड देखें।"""
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

If account is inactive, contact your institution director.""",
        "answer_hi": """यदि आप अपना पासवर्ड भूल गए हैं:

1. **डिफ़ॉल्ट पासवर्ड:** नए छात्रों के लिए, डिफ़ॉल्ट पासवर्ड आपका फ़ोन नंबर है
2. **पासवर्ड भूले:** लॉगिन पेज पर "Forgot Password" पर क्लिक करें (यदि उपलब्ध हो)
3. **संस्था से संपर्क करें:** पासवर्ड रीसेट के लिए अपनी संस्था के एडमिन/निदेशक से संपर्क करें

**लॉगिन क्रेडेंशियल:**
- उपयोगकर्ता नाम: आपका ईमेल पता
- पासवर्ड: फ़ोन नंबर (डिफ़ॉल्ट) या आपका बदला हुआ पासवर्ड

**सुरक्षा सुझाव:**
- पहली लॉगिन के बाद डिफ़ॉल्ट पासवर्ड बदलें
- मजबूत पासवर्ड का उपयोग करें
- क्रेडेंशियल साझा न करें
- साझा उपकरणों से लॉगआउट करें

यदि खाता निष्क्रिय है, तो अपनी संस्था के निदेशक से संपर्क करें।"""
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

Access the platform at your institution's provided URL.""",
        "answer_hi": """आपके लॉगिन क्रेडेंशियल:

**उपयोगकर्ता नाम:** आपका ईमेल पता (पंजीकरण के दौरान प्रदान किया गया)

**पासवर्ड:**
- डिफ़ॉल्ट: आपका फ़ोन नंबर
- सुरक्षा के लिए पहली लॉगिन के बाद बदलें

**लॉगिन प्रक्रिया:**
1. लॉगिन पेज पर जाएं
2. उपयोगकर्ता नाम के रूप में ईमेल दर्ज करें
3. पासवर्ड दर्ज करें (पहली बार के लिए फ़ोन नंबर)
4. लॉगिन पर क्लिक करें
5. प्रोफ़ाइल सेटिंग्स में पासवर्ड बदलें

**समस्या निवारण:**
- सुनिश्चित करें कि ईमेल सही है
- पासवर्ड के रूप में फ़ोन नंबर आज़माएं
- जांचें कि खाता सक्रिय है
- समस्या बनी रहने पर संस्था से संपर्क करें

अपनी संस्था द्वारा प्रदान किए गए URL पर प्लेटफ़ॉर्म एक्सेस करें।"""
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

Navigate through the menu to access different sections.""",
        "answer_hi": """छात्र डैशबोर्ड की विशेषताएं:

**अवलोकन:**
- आपकी प्रोफ़ाइल जानकारी
- नामांकित कोर्स
- समग्र प्रगति

**कोर्स:**
- नामांकित कोर्स देखें
- मॉड्यूल-वार प्रगति
- पूर्णता प्रतिशत
- प्राप्त अंक

**भुगतान:**
- भुगतान इतिहास
- लंबित फ़ीस
- रसीद डाउनलोड करें
- बैलेंस जानकारी

**परीक्षाएं:**
- निर्धारित परीक्षाएं
- ऑनलाइन परीक्षाएं दें
- परिणाम देखें
- परीक्षा इतिहास

**प्रमाण पत्र:**
- प्रमाण पत्र डाउनलोड करें
- प्रमाण पत्र विवरण देखें
- सत्यापन QR कोड

**प्रोफ़ाइल:**
- व्यक्तिगत जानकारी अपडेट करें
- पासवर्ड बदलें
- छात्र ID देखें

विभिन्न अनुभागों तक पहुंचने के लिए मेनू में नेविगेट करें।"""
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

Each role has specific permissions for data security.""",
        "answer_hi": """RTS में उपयोगकर्ता भूमिकाएं:

1. **सुपर एडमिन (सिस्टम निदेशक)**
   - पूर्ण सिस्टम एक्सेस
   - सभी संस्थाओं का प्रबंधन

2. **संस्था निदेशक**
   - अपनी संस्था तक पूर्ण एक्सेस
   - स्टाफ और छात्रों का प्रबंधन
   - स्टाफ दरें निर्धारित करता है

3. **अकाउंटेंट**
   - अंक दर्ज करें
   - भुगतान प्रबंधित करें
   - रिपोर्ट बनाएं

4. **रिसेप्शनिस्ट**
   - केवल भुगतान रिकॉर्ड करें
   - रसीद बनाएं

5. **स्टाफ मैनेजर**
   - छात्रों और स्टाफ का प्रबंधन
   - उपस्थिति दर्ज करें
   - दैनिक संचालन

6. **स्टाफ**
   - उपस्थिति दर्ज करें
   - छात्र देखें
   - सीमित एक्सेस

7. **छात्र**
   - अपना डेटा देखें
   - परीक्षा दें
   - सामग्री एक्सेस करें

डेटा सुरक्षा के लिए प्रत्येक भूमिका के पास विशिष्ट अनुमतियां हैं।"""
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
- Use this chatbot (Raj) for instant answers
- Available 24/7 in your dashboard

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

For urgent matters, visit your institution office directly.""",
        "answer_hi": """सहायता प्राप्त करना:

**इन-ऐप सहायता:**
- तत्काल उत्तरों के लिए इस चैटबॉट (राज) का उपयोग करें
- आपके डैशबोर्ड में 24/7 उपलब्ध

**संस्था सहायता:**
- अपने संस्था निदेशक से संपर्क करें
- भुगतान समस्याओं के लिए अकाउंटेंट से संपर्क करें
- सामान्य प्रश्नों के लिए स्टाफ मैनेजर से संपर्क करें

**सामान्य समस्याएं:**
- लॉगिन समस्याएं: पासवर्ड के रूप में फ़ोन नंबर आज़माएं
- भुगतान समस्याएं: रिसेप्शनिस्ट/अकाउंटेंट से संपर्क करें
- प्रमाण पत्र में देरी: अकाउंटेंट से संपर्क करें
- उपस्थिति समस्याएं: 7 दिनों के भीतर स्टाफ मैनेजर को रिपोर्ट करें

**तकनीकी समस्याएं:**
- ब्राउज़र कैश साफ़ करें
- अलग ब्राउज़र आज़माएं
- इंटरनेट कनेक्शन जांचें
- संस्था एडमिन से संपर्क करें

अत्यावश्यक मामलों के लिए, सीधे अपनी संस्था के कार्यालय में जाएं।"""
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

Your progress is updated after each module exam is verified by staff.""",
        "answer_hi": """अपनी प्रगति ट्रैक करना:

**छात्र डैशबोर्ड में:**
1. "Courses" अनुभाग पर जाएं
2. अपना नामांकित कोर्स चुनें
3. मॉड्यूल-वार प्रगति देखें

**प्रगति जानकारी:**
- कोर्स में कुल मॉड्यूल
- पूर्ण किए गए मॉड्यूल
- प्रगति में मॉड्यूल
- शुरू न किए गए मॉड्यूल
- समग्र पूर्णता प्रतिशत
- प्रत्येक मॉड्यूल में प्राप्त अंक

**मॉड्यूल स्थिति:**
- **शुरू नहीं:** मॉड्यूल अभी शुरू नहीं हुआ
- **प्रगति में:** वर्तमान में अध्ययन कर रहे हैं
- **पूर्ण:** मॉड्यूल परीक्षा उत्तीर्ण
- **असफल:** उत्तीर्ण नहीं हुए (दोबारा ले सकते हैं)

**अंक प्रदर्शन:**
- प्राप्त अंक / कुल अंक
- प्रतिशत
- उत्तीर्ण/अनुत्तीर्ण स्थिति
- परीक्षा तिथि

स्टाफ द्वारा प्रत्येक मॉड्यूल परीक्षा सत्यापित होने के बाद आपकी प्रगति अपडेट होती है।"""
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
