from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, HTTPException, status
from app.models import LoginRequest, LogoutRequest, RegisterRequest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import bcrypt
from jose import jwt

from app.utils import check_token_expiry, hash_token, is_existing_token

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Вспомогательные методы
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    jti = secrets.token_urlsafe(16)
    return jwt.encode(
        {"sub": user_id, "jti": jti},
        SECRET_KEY, 
        algorithm=ALGORITHM
    )

router = APIRouter(prefix="/api")

# Регистрация
@router.post("/register")
def register(request: RegisterRequest):
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if result:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        
        password_hash = get_password_hash(request.password)
        
        db.execute(
            text("""
                INSERT INTO users (firstname, surname, email, password_hash) 
                VALUES (:firstname, :surname, :email, :password_hash)
            """),
            {
                "firstname": request.firstname,
                "surname": request.surname,
                "email": request.email,
                "password_hash": password_hash
            }
        )
        
        db.commit()
        return {"status": "success", "message": "Пользователь зарегистрирован"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Авторизация
@router.post("/login")
def login(request: LoginRequest):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=400, detail="Пользователь с таким email не существует")
        
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Неверный пароль")
        
        token_count_result = db.execute(
            text("SELECT COUNT(*) FROM personal_access_tokens WHERE user_id = :user_id"),
            {"user_id": user.id}
        ).fetchone()
        token_count = token_count_result[0] if token_count_result else 0
        
        MAX_COUNT_ACCESS_TOKENS = int(os.getenv("MAX_COUNT_ACCESS_TOKENS", 3))
        ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

        if token_count >= MAX_COUNT_ACCESS_TOKENS:
            oldest_token = db.execute(
                text("""
                    SELECT id FROM personal_access_tokens 
                    WHERE user_id = :user_id 
                    ORDER BY created_at ASC 
                    LIMIT 1
                """),
                {"user_id": user.id}
            ).fetchone()
            
            if oldest_token:
                db.execute(
                    text("DELETE FROM personal_access_tokens WHERE id = :token_id"),
                    {"token_id": oldest_token.id}
                )
        
        token = create_jwt_token(str(user.id))
        expires_at = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        db.execute(
            text("""
                INSERT INTO personal_access_tokens (user_id, token, expires_at) 
                VALUES (:user_id, :token, :expires_at)
            """),
            {
                "user_id": user.id,
                "token": hash_token(token),
                "expires_at": expires_at
            }
        )

        db.commit()
        return {
            "status": "success", 
            "token": token,
            "user_id": user.id,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Конец сессии
@router.delete("/logout")
def logout(request: LogoutRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)

    if not is_existing_token(db, request.token):
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден"
        )
    
    try:
        db.execute(
            text("DELETE FROM personal_access_tokens WHERE token = :token"),
            {"token": hash_token(request.token)}
        )
        db.commit()
        return {"out_token": "success"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    
