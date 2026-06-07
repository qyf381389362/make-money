from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import journal, positions, prices

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Make Money API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions.router)
app.include_router(journal.router)
app.include_router(prices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
