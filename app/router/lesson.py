from fastapi import APIRouter, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import AskLessonRequest, CreateLessonRequest, TokenRequest, UpdateLessonRequest
from app.utils import check_token_expiry, get_course_by_lesson, get_user_by_token, hash_token, is_admin, is_existing_token, is_user_in_course, query_ai

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

lesson_router = APIRouter(prefix="/api/lesson", tags=["Lesson API"])

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

# Создание нового урока
@lesson_router.post("/create/course/{course_id}")
def create_lesson(course_id: int, request: CreateLessonRequest):
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
                INSERT INTO lessons (title, description, education_content, duration_minutes, course_id) 
                VALUES (:title, :description, :education_content, :duration_minutes, :course_id)
            """),
            {
                "title": request.title,
                "description": request.description,
                "education_content": request.education_content,
                "duration_minutes": request.duration_minutes,
                "course_id": course_id
            }
        )
        db.commit()
        return {"status": "success", "message": "Урок создан"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Внесение изменений в урок
@lesson_router.put("/update/{lesson_id}")
def update_lesson(lesson_id: int, request: UpdateLessonRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ошибка доступа"
        )
    try:
        lesson = db.execute(
            text("SELECT id FROM lessons WHERE id = :lesson_id"),
            {"lesson_id": lesson_id}
        ).fetchone()

        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")
        
        if request.title is None and request.description is None and request.education_content is None and request.duration_minutes is None:
            raise HTTPException(
                status_code=400, 
                detail="Не указаны данные для изменения"
            )
        
        update_fields = []
        params = {"lesson_id": lesson_id}
        
        if request.title is not None:
            update_fields.append("title = :title")
            params["title"] = request.title
            
        if request.description is not None:
            update_fields.append("description = :description")
            params["description"] = request.description
            
        if request.education_content is not None:
            update_fields.append("education_content = :education_content")
            params["education_content"] = request.education_content

        if request.duration_minutes is not None:
            update_fields.append("duration_minutes = :duration_minutes")
            params["duration_minutes"] = request.duration_minutes
        
        query = f"UPDATE lessons SET {', '.join(update_fields)} WHERE id = :lesson_id"
        db.execute(text(query), params)
        
        db.commit()
        return {"status": "success", "message": "Урок обновлен"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()
    
# Удаление урока
@lesson_router.delete("/delete/{lesson_id}")
def delete_lesson(lesson_id: int, request: TokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    if not is_admin(db, request.token):
        raise HTTPException(status_code=403, detail="Ошибка доступа")
    
    try:
        lesson = db.execute(
            text("SELECT id FROM lessons WHERE id = :lesson_id"),
            {"lesson_id": lesson_id}
        ).fetchone()

        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")
        
        db.execute(
            text("DELETE FROM lessons WHERE id = :lesson_id"),
            {"lesson_id": lesson_id}
        )
        
        db.commit()
        return {"status": "success", "message": "Урок удален"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Отметка урока как пройденного
@lesson_router.put("/complete/{lesson_id}")
def complete_lesson(lesson_id: int, request: TokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    
    user_id = get_user_by_token(db, request.token)
    
    lesson_result = db.execute(
        text("SELECT course_id FROM lessons WHERE id = :lesson_id"),
        {"lesson_id": lesson_id}
    ).fetchone()
    
    if not lesson_result:
        raise HTTPException(status_code=404, detail="Урок не найден")
    
    course_id = lesson_result[0]
    
    if not is_user_in_course(db, request.token, course_id):
        raise HTTPException(status_code=403, detail="Ошибка доступа")

    try:
        db.execute(
            text("""
                UPDATE usersprogress 
                SET is_completed = TRUE
                WHERE user_id = :user_id AND lesson_id = :lesson_id
            """),
            {
                "user_id": user_id,
                "lesson_id": lesson_id
            }
        )
        
        db.commit()
        return {"status": "success", "message": "Урок отмечен как завершённый"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

# Запрос к нейросети с вопросом по уроку
@lesson_router.post("/{lesson_id}/ask")
def ask_question(lesson_id: int, request: AskLessonRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    
    lesson_result = db.execute(
        text("SELECT * FROM lessons WHERE id = :lesson_id"),
        {"lesson_id": lesson_id}
    ).fetchone()
    
    if not lesson_result:
        raise HTTPException(status_code=404, detail="Урок не найден")

    if not is_user_in_course(db, request.token, lesson_result.course_id) and not is_admin(db, request.token):
        raise HTTPException(status_code=403, detail="Ошибка доступа")

    try:
        prompt = f"""Ты - AI-репетитор. 

            Контекст урока:
            1) Название урока: {lesson_result.title}
            2) Описание урока: {lesson_result.description}  
            3) Обучающий контент: {lesson_result.education_content}

            Вопрос студента: {request.ask}

            Требования к ответу:
            - ОТВЕЧАЙ ТОЛЬКО ОБЫЧНЫМ ТЕКСТОМ БЕЗ ФОРМАТИРОВАНИЯ
            - ЗАПРЕЩЕНО: Markdown, backticks ``, звездочки **, подчеркивания __
            - ЗАПРЕЩЕНО: отдельные блоки для кода
            - ЗАПРЕЩЕНО: символы ``` в любом виде
            - Для примеров кода пиши: функция print("текст") в строку
            - Используй обычные пробелы между словами
            - Пиши как обычное сообщение в чате

            Дай развернутый, но четкий ответ, основанный на предоставленном контексте. Если ответа в контексте нет, так и скажи."""
        
        response = query_ai(prompt)

        db.commit()
        return {"status": "success", "responseai": response}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()