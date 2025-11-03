from fastapi import APIRouter, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import TokenRequest
from app.utils import check_token_expiry, hash_token, is_admin, is_existing_token

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

lesson_router = APIRouter(prefix="/api/lesson")

# Получение всех уроков
@lesson_router.post("")
def get_lessons(request: TokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    try:
        lessons = db.execute(
            text("SELECT id, title, description, education_content, course_id, duration_minutes FROM lessons")
        ).fetchall()
        
        if not lessons:
            raise HTTPException(status_code=404, detail="Уроки не найдены")
        
        lessons_list = []
        for lesson in lessons:
            lessons_list.append({
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "education_content": lesson.education_content,
                "course_id": lesson.course_id,
                "duration_minutes": lesson.duration_minutes,
            })
        
        return {
            "status": "success",
            "count_lessons": len(lessons_list),
            "lessons": lessons_list
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()