from fastapi import APIRouter, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import CreateCourseRequest, TokenRequest, UpdateCourseRequest
from app.utils import get_user_by_token, is_admin, check_token_expiry, is_user_in_course

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

course_router = APIRouter(prefix="/api/course", tags=["Course API"])

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
@course_router.post("/{course_id}/lessons")
def get_lessons_by_course(course_id: int, request: TokenRequest):
    db = SessionLocal()
    full_access = False
    try:
        if (request.token != None):
            check_token_expiry(db, request.token)
            if is_admin(db, request.token) or is_user_in_course(db, request.token, course_id):
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

# Создание нового курса
@course_router.post("/create")
def create_course(request: CreateCourseRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    try:
        db.execute(
            text("""
                INSERT INTO courses (title, description, price) 
                VALUES (:title, :description, :price)
            """),
            {
                "title": request.title,
                "description": request.description,
                "price": request.price,
            }
        )
        db.commit()
        return {"status": "success", "message": "Курс создан"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Внесение изменений в курс
@course_router.put("/update/{course_id}")
def update_course(course_id: int, request: UpdateCourseRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    try:
        course = db.execute(
            text("SELECT id FROM courses WHERE id = :course_id"),
            {"course_id": course_id}
        ).fetchone()

        if not course:
            raise HTTPException(status_code=404, detail="Курс не найден")
        
        if request.title is None and request.description is None and request.price is None:
            raise HTTPException(
                status_code=400, 
                detail="Не указаны данные для изменения"
            )
        
        update_fields = []
        params = {"course_id": course_id}
        
        if request.title is not None:
            update_fields.append("title = :title")
            params["title"] = request.title
            
        if request.description is not None:
            update_fields.append("description = :description")
            params["description"] = request.description
            
        if request.price is not None:
            update_fields.append("price = :price")
            params["price"] = request.price
        
        query = f"UPDATE courses SET {', '.join(update_fields)} WHERE id = :course_id"
        db.execute(text(query), params)
        
        db.commit()
        return {"status": "success", "message": "Курс обновлен"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()
    
# Удаление курса
@course_router.delete("/delete/{course_id}")
def delete_course(course_id: int, request: TokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(status_code=403, detail="Ошибка доступа")
    
    try:
        course = db.execute(
            text("SELECT id FROM courses WHERE id = :course_id"),
            {"course_id": course_id}
        ).fetchone()

        if not course:
            raise HTTPException(status_code=404, detail="Курс не найден")
        
        db.execute(
            text("DELETE FROM courses WHERE id = :course_id"),
            {"course_id": course_id}
        )
        
        db.commit()
        return {"status": "success", "message": "Курс и все связные уроки удалены"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()