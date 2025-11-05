import re
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import CheckTaskRequest, TokenRequest
from app.utils import check_token_expiry, get_user_by_token, is_admin, query_ai

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

task_router = APIRouter(prefix="/api/task", tags=["Task API"])

# Получение всех задач пользователя
@task_router.post("")
def get_tasks(request: TokenRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)

    user_id = get_user_by_token(db, request.token)
    try:
        tasks = db.execute(
            text("""
                SELECT *
                FROM tasks 
                WHERE user_id = :user_id 
            """),
            {"user_id": user_id}
        ).fetchall()
        
        if not tasks:
            raise HTTPException(status_code=404, detail="Задачи не найдены")
        
        tasks_list = []
        for task in tasks:
            task_data = {
                "id": task.id,
                "task": task.task,
                "is_answer_right": task.is_answer_right,
                "answer_user": task.answer_user
            }
            
            if task.is_answer_right:
                task_data["answer_right"] = task.answer_right
            
            tasks_list.append(task_data)
        
        return {
            "status": "success",
            "count_tasks": len(tasks_list),
            "tasks": tasks_list
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()

@task_router.put("/{task_id}/check-task")
def check_task(task_id: int, request: CheckTaskRequest):
    db = SessionLocal()
    check_token_expiry(db, request.token)
    
    user_id = get_user_by_token(db, request.token)
    
    task_result = db.execute(
        text("SELECT * FROM tasks WHERE id = :task_id AND user_id = :user_id"),
        {"task_id": task_id, "user_id": user_id}
    ).fetchone()
    
    if not task_result:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    if task_result.is_answer_right:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Верный ответ на задачу уже был предоставлен"
        )
    
    task = task_result.task
    answer_right = task_result.answer_right

    prompt = f"""
                Задача: {task}
                Ответ студента: {request.answer}
                Эталонное решение: {answer_right}

                Проанализируй ответ студента по следующим критериям:
                1. Корректность синтаксиса (правильность написания кода)
                2. Соответствие логике задачи
                3. Достижение поставленной цели
                4. Использование правильных конструкций языка

                Ответ студента считается ВЕРНЫМ (true), если:
                - Синтаксис корректен
                - Логика соответствует задаче  
                - Достигнут ожидаемый результат
                - Допускаются незначительные отклонения в формулировках

                Ответ студента считается НЕВЕРНЫМ (false), если:
                - Синтаксические ошибки
                - Неправильная логика
                - Не достигнут требуемый результат
                - Существенные отклонения от эталона

                Ответ дай СТРОГО одним словом: true или false
            """
        
    response = query_ai(prompt)

    is_correct = response.strip().lower() == 'true'

    try:
        db.execute(
            text("""
                UPDATE tasks 
                SET is_answer_right = :is_correct, answer_user = :answer
                WHERE id = :task_id AND user_id = :user_id
            """),
            {
                "is_correct": is_correct,
                "answer": request.answer,
                "task_id": task_id,
                "user_id": user_id
            }
        )
        
        db.commit()
        return {
            "status": "success", 
            "is_correct": is_correct,
            "ai_response": response
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    finally:
        db.close()
