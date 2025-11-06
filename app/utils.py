from datetime import datetime, timezone
import json
import os
import re
from dotenv import load_dotenv
from fastapi import HTTPException
import gigachat
from sqlalchemy import text
from gigachat import GigaChat
import hashlib
from json_repair import repair_json

load_dotenv()

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
def check_token_expiry(db, token: str) -> bool:
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

# Получение user_id по Email
def get_user_by_email(db, email: str) -> int:
    result = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Пользователь с таким Email не найден")

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

# Проверка пользователя на участие в курсе
def is_user_in_course(db, token: str, course_id: int) -> bool:
    user_id = get_user_by_token(db, token)

    response = db.execute(
        text("""
            SELECT id
            FROM usersprogress 
            WHERE user_id = :user_id AND course_id = :course_id
        """),
        {"user_id": user_id, "course_id": course_id}
    ).fetchone()

    if response is not None:
        return True
    
    return False

# Получение курса по идентификатору урока
def get_course_by_lesson(db, lesson_id: int) -> int:
    result = db.execute(
        text("SELECT course_id FROM lessons WHERE id = :lesson_id"),
        {"lesson_id": lesson_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Урок не найден")

    return result[0]

# Запрос к нейросети GigaChat
def query_ai(prompt: str):
    try:
        token = os.getenv("GIGACHAT_AUTHORIZATION_KEY")
        giga = gigachat.GigaChat(
            credentials=token,
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS"
        )
        
        response = giga.chat(prompt)
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Ошибка: {str(e)}"
    
# Обработка достижений
def process_achievement_event(db, badge_type: str, user_id: int, task_complete: bool = None):
    stats = db.execute(
        text("SELECT * FROM usersprogress_stats WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    
    if not stats:
        db.execute(
            text("INSERT INTO usersprogress_stats (user_id) VALUES (:user_id)"),
            {"user_id": user_id}
        )
        stats = db.execute(
            text("SELECT * FROM usersprogress_stats WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
    
    if badge_type == "lesson_complete":
        new_lesson_count = stats.lesson_complete + 1
        db.execute(
            text("UPDATE usersprogress_stats SET lesson_complete = :count WHERE user_id = :user_id"),
            {"count": new_lesson_count, "user_id": user_id}
        )
    
        achievements = db.execute(
            text("SELECT * FROM badges WHERE badge_type = 'lesson_complete' AND badge_value <= :count"),
            {"count": new_lesson_count}
        ).fetchall()
        
        for achievement in achievements:
            existing = db.execute(
                text("SELECT * FROM user_badges WHERE user_id = :user_id AND badge_id = :badge_id"),
                {"user_id": user_id, "badge_id": achievement.id}
            ).fetchone()
            
            if not existing:
                db.execute(
                    text("INSERT INTO user_badges (user_id, badge_id) VALUES (:user_id, :badge_id)"),
                    {"user_id": user_id, "badge_id": achievement.id}
                )
    
    elif badge_type == "task_completed":
        if task_complete == True:
            new_streak = stats.tasks_streak + 1
            db.execute(
                text("""
                    UPDATE usersprogress_stats 
                    SET tasks_streak = :streak, 
                        max_streak = GREATEST(max_streak, :streak) 
                    WHERE user_id = :user_id
                """),
                {"streak": new_streak, "user_id": user_id}
            )
            
            streak_achievements = db.execute(
                text("SELECT * FROM badges WHERE badge_type = 'tasks_streak' AND badge_value <= :streak"),
                {"streak": new_streak}
            ).fetchall()
            
            for achievement in streak_achievements:
                existing = db.execute(
                    text("SELECT * FROM user_badges WHERE user_id = :user_id AND badge_id = :badge_id"),
                    {"user_id": user_id, "badge_id": achievement.id}
                ).fetchone()
                
                if not existing:
                    db.execute(
                        text("INSERT INTO user_badges (user_id, badge_id) VALUES (:user_id, :badge_id)"),
                        {"user_id": user_id, "badge_id": achievement.id}
                    )
        else:
            db.execute(
                text("UPDATE usersprogress_stats SET tasks_streak = 0 WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
    
    elif badge_type == "course_complete":
        new_course_count = stats.course_complete + 1
        db.execute(
            text("UPDATE usersprogress_stats SET course_complete = :count WHERE user_id = :user_id"),
            {"count": new_course_count, "user_id": user_id}
        )
        
        course_achievements = db.execute(
            text("SELECT * FROM badges WHERE badge_type = 'course_complete' AND badge_value <= :count"),
            {"count": new_course_count}
        ).fetchall()
        
        for achievement in course_achievements:
            existing = db.execute(
                text("SELECT * FROM user_badges WHERE user_id = :user_id AND badge_id = :badge_id"),
                {"user_id": user_id, "badge_id": achievement.id}
            ).fetchone()
            
            if not existing:
                db.execute(
                    text("INSERT INTO user_badges (user_id, badge_id) VALUES (:user_id, :badge_id)"),
                    {"user_id": user_id, "badge_id": achievement.id}
                )
    
    db.commit()
