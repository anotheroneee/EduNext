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