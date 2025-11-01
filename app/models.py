from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class RegisterRequest(BaseModel):
    firstname: str
    surname: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str