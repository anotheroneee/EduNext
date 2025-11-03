from fastapi import APIRouter, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import TokenRequest
from app.utils import get_user_by_token, is_admin, check_token_expiry

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

course_router = APIRouter(prefix="/api/course")

# Получение всех курсов
@course_router.get("")
def get_courses():
    db = SessionLocal()
    try:
        courses = db.execute(
            text("SELECT id, title, description, price FROM courses")
        ).fetchall()
        
        if not courses:
            raise HTTPException(status_code=404, detail="Курсы не найдены")
        
        courses_list = []
        for course in courses:
            courses_list.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "price": course.price if course.price else 0
            })
        
        return {
            "status": "success",
            "count_courses": len(courses_list),
            "courses": courses_list
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Получение уроков в определенном курсе
@course_router.post("/course/{course_id}/lessons")
def get_lessons_by_course(course_id: int, request: TokenRequest):
    db = SessionLocal()
    full_access = False
    try:
        if (request.token != None):
            check_token_expiry(db, request.token)

            user_id = get_user_by_token(db, request.token)

            response = db.execute(
                text("""
                    SELECT id
                    FROM usersprogress 
                    WHERE user_id = :user_id AND course_id = :course_id
                """),
                {"user_id": user_id, "course_id": course_id}
            ).fetchone()

            if is_admin(db, request.token) or response is not None:
                full_access = True
            
        lessons = db.execute(
            text("""
                SELECT id, title, description, education_content, course_id, duration_minutes 
                FROM lessons 
                WHERE course_id = :course_id 
            """),
            {"course_id": course_id}
        ).fetchall()
        
        if full_access == True:
            lessons_list = [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "education_content": lesson.education_content,
                    "course_id": lesson.course_id,
                    "duration_minutes": lesson.duration_minutes
                }
                for lesson in lessons
            ]
        
        else:
            lessons_list = [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "course_id": lesson.course_id,
                    "duration_minutes": lesson.duration_minutes
                }
                for lesson in lessons
            ]
        return {
            "status": "success",
            "course_id": course_id,
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