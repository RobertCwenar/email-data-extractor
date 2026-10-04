from fastapi import FastAPI

from app.api.routes.offers import router as offers_router

app = FastAPI(title="Job Market Monitor")

app.include_router(offers_router)


@app.get("/")
def root():
    return {"message": "Job Market Monitor API"}
