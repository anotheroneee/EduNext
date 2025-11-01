import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from app.router.user import router

load_dotenv()

app = FastAPI()

app.include_router(router)

@app.get("/")
async def health_check():
    return {"status": "ok", "services": ["edunextapi"]}

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("DEPLOY_HOST"), port=int(os.getenv("DEPLOY_PORT")))