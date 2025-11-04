from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date


# User
class RegisterRequest(BaseModel):
    firstname: str
    surname: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenRequest(BaseModel):
    token: Optional[str] = None

class EmailTokenRequest(BaseModel):
    token: Optional[str] = None
    email: EmailStr

class VerifyRequest(BaseModel):
    code: str
    email: EmailStr

# Course
class CreateCourseRequest(BaseModel):
    token: str
    title: str
    description: str
    price: int

class UpdateCourseRequest(BaseModel):
    token: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None

# Lesson
class CreateLessonRequest(BaseModel):
    token: str
    title: str
    description: str
    education_content: str
    duration_minutes: int

class UpdateLessonRequest(BaseModel):
    token: str
    title: Optional[str] = None
    description: Optional[str] = None
    education_content: Optional[str] = None
    duration_minutes: Optional[int] = None