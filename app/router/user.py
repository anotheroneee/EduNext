from datetime import datetime, timedelta
import random
import secrets
import smtplib
from fastapi import APIRouter, HTTPException, status
from app.models import EmailTokenRequest, LoginRequest, TokenRequest, RegisterRequest, VerifyRequest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import bcrypt
from jose import jwt
from email.mime.text import MIMEText

from app.utils import check_token_expiry, get_user_by_email, hash_token, is_admin, is_existing_token

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Вспомогательные методы
def get_text_hash(text: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(text.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_text_hash(plain_text: str, hashed_text: str) -> bool:
    return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_text.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    jti = secrets.token_urlsafe(16)
    return jwt.encode(
        {"sub": user_id, "jti": jti},
        SECRET_KEY, 
        algorithm=ALGORITHM
    )

def send_verify_code_to_email(db, user_id: int, email: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    code = random.randint(100000, 999999)
    
    subject = "Подтверждение email"

    message = f"""Код подтверждения: {code}"""

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = smtp_username
    msg['To'] = email
    
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    server.send_message(msg)
    server.quit()

    db.execute(
        text("DELETE FROM verify_codes WHERE user_id = :user_id"),
        {"user_id": user_id}
    )

    db.execute(
        text("""
            INSERT INTO verify_codes (user_id, code_hash) 
            VALUES (:user_id, :code)
        """),
        {
            "user_id": user_id,
            "code": get_text_hash(str(code))
        }
    )


user_router = APIRouter(prefix="/api/user", tags=["User API"])

# Регистрация
@user_router.post("/register")
def register(request: RegisterRequest):
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if result:
            raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
        
        password_hash = get_text_hash(request.password)
        
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

        result = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        user_id = result[0]
        send_verify_code_to_email(db, user_id, request.email)

        db.commit()
        return {"status": "success", "message": "Пользователь зарегистрирован. Код подтверждения отправлен на указаный Email"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Подтверждение/активация пользователя
@user_router.put("/verify")
def verify(request: VerifyRequest):
    db = SessionLocal()
    try:
        user_id = get_user_by_email(db, request.email)

        is_verify = db.execute(
            text("SELECT is_verify FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if is_verify[0]:
            raise HTTPException(status_code=400, detail="Аккаунт уже подтверждён")
        
        code_result = db.execute(
            text("SELECT code_hash FROM verify_codes WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()

        if not code_result:
            raise HTTPException(status_code=400, detail="Код подтверждения не найден")

        if not verify_text_hash(request.code, code_result[0]):
            raise HTTPException(status_code=400, detail="Неверный код подтверждения")
            
        db.execute(
            text("UPDATE users SET is_verify = TRUE WHERE id = :user_id"),
            {"user_id": user_id}
        )

        db.execute(
            text("DELETE FROM verify_codes WHERE user_id = :user_id"),
            {"user_id": user_id}
        )

        db.commit()
        return {"status": "success", "message": "Учётная запись пользователя активирована"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Авторизация
@user_router.post("/login")
def login(request: LoginRequest):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=400, detail="Пользователь с таким email не существует")
        
        if not verify_text_hash(request.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Неверный пароль")
        
        if not user.is_verify:
            send_verify_code_to_email(db, user.id, user.email)
            raise HTTPException(
                status_code=403,
                detail="Аккаунт не подтвержден. Код подтверждения отправлен на email"
            )

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
@user_router.delete("/logout")
def logout(request: TokenRequest):
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
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Зачисление пользователя на курс
@user_router.post("/enroll/{course_id}")
def enroll_user_to_course(course_id: int, request: EmailTokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    
    try:
        user_id = get_user_by_email(db, request.email)
        result = db.execute(
            text("SELECT id FROM usersprogress WHERE user_id = :user_id AND course_id = :course_id"),
            {"user_id": user_id, "course_id": course_id}
        ).fetchone()

        if result:
            raise HTTPException(status_code=400, detail="Пользователь уже зачислен на данный курс")
        
        lessons = db.execute(
            text("SELECT id FROM lessons WHERE course_id = :course_id"),
            {"course_id": course_id}
        ).fetchall()

        for lesson in lessons:
            db.execute(
                text("""
                    INSERT INTO usersprogress (user_id, course_id, lesson_id) 
                    VALUES (:user_id, :course_id, :lesson_id)
                """),
                {
                    "user_id": user_id,
                    "course_id": course_id,
                    "lesson_id": lesson.id
                }
            )
        
        db.commit()
        return {"status": "success", "message": "Пользователь зачислен на курс"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Отчисление пользователя с курса
@user_router.delete("/dismiss/{course_id}")
def dismiss_user_to_course(course_id: int, request: EmailTokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    
    try:
        user_id = get_user_by_email(db, request.email)
        result = db.execute(
            text("SELECT id FROM usersprogress WHERE user_id = :user_id AND course_id = :course_id"),
            {"user_id": user_id, "course_id": course_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=400, detail="Пользователь не зачислен на данный курс")
        
        lessons = db.execute(
            text("SELECT id FROM lessons WHERE course_id = :course_id"),
            {"course_id": course_id}
        ).fetchall()

        for lesson in lessons:
            db.execute(
                text("""
                    DELETE FROM usersprogress 
                    WHERE user_id = :user_id AND course_id = :course_id AND lesson_id = :lesson_id
                """),
                {
                    "user_id": user_id,
                    "course_id": course_id,
                    "lesson_id": lesson.id
                }
            )
        
        db.commit()
        return {"status": "success", "message": "Пользователь отчислен с курса"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Выдача пользователю прав администратора
@user_router.put("/make-admin")
def dismiss_user_to_course(request: EmailTokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    
    try:
        user_id = get_user_by_email(db, request.email)
        result = db.execute(
            text("SELECT id, firstname, surname FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=400, detail="Пользователь с указанным Email не найден")
        
        db.execute(
            text("UPDATE users SET is_admin = TRUE WHERE id = :user_id"),
            {"user_id": user_id}
        )

        db.commit()
        return {"status": "success", "message": "Пользователь был назначен администратором"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()
