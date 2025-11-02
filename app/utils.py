from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import text
import hashlib

# Проверка существования токена
def is_existing_token(db, token: str) -> bool:
    result = db.execute(
        text("SELECT id FROM personal_access_tokens WHERE token = :token"),
        {
            "token": hash_token(token),
        }
    ).fetchone()
    
    if not result: return False
    return True

# Хэш токена
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# Проверка срока действия токена
def is_token_expiry(db, token: str) -> bool:
    result = db.execute(
        text("SELECT id, expires_at FROM personal_access_tokens WHERE token = :token"),
        {"token": hash_token(token)}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Токен не найден")
    
    token_id, expires_at = result
    
    if expires_at and expires_at < datetime.now(timezone.utc):
        db.execute(
            text("DELETE FROM personal_access_tokens WHERE id = :id"),
            {"id": token_id}
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Токен недействителен")
    
    return True

# Получение user_id по токену
def get_user_by_token(db, token: str) -> int:
    result = db.execute(
        text("SELECT user_id FROM personal_access_tokens WHERE token = :token"),
        {"token": hash_token(token)}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Токен не найден")

    return result[0]

# Проверка пользователя на роль администратора
def is_admin(db, token: str) -> bool:
    user_id = get_user_by_token(db, token)
    
    user_is_admin = db.execute(
        text("SELECT is_admin FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    
    if not user_is_admin:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return user_is_admin[0]
    
    