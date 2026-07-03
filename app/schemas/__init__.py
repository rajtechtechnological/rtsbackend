from app.schemas.user import UserCreate, UserLogin, UserUpdate, UserResponse, Token, TokenData, Role
from app.schemas.institution import (
    InstitutionCreate, InstitutionUpdate, InstitutionStatusUpdate, InstitutionResponse,
)
from app.schemas.student import (
    StudentCreate, StudentRegister, StudentUpdate, StudentListItem, StudentResponse,
    CourseEnrollmentCreate, FeePaymentCreate, FeePaymentResponse,
)
from app.schemas.batch import BatchCreate, BatchUpdate, BatchResponse
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.schemas.staff import (
    StaffCreate, StaffUpdate, StaffResponse,
    AttendanceCreate, AttendanceBatchCreate, AttendanceResponse,
)
from app.schemas.payroll import PayrollGenerate, PayrollResponse, CertificateGenerate, CertificateResponse
