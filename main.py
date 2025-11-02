import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from app.router.user import user_router
from app.router.course import course_router
from app.router.lesson import lesson_router

load_dotenv()

app = FastAPI()

app.include_router(user_router)
app.include_router(course_router)
app.include_router(lesson_router)

@app.get("/")
async def health_check():
    return {"status": "ok", "services": ["edunextapi"]}

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("DEPLOY_HOST"), port=int(os.getenv("DEPLOY_PORT")))