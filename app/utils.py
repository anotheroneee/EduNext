from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import text
import hashlib

def is_existing_token(db, token: str) -> bool:
    result = db.execute(
        text("SELECT id FROM personal_access_tokens WHERE token = :token"),
        {
            "token": hash_token(token),
        }
    ).fetchone()
    
    if not result: return False
    return True

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def check_token_expiry(db, token: str) -> bool:
    result = db.execute(
        text("SELECT id, expires_at FROM personal_access_tokens WHERE token = :token"),
        {"token": hash_token(token)}
    ).fetchone()
    
    print(result)
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