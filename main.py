from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from search import router as search_router

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth_router, prefix="/auth")
app.include_router(search_router, prefix="/buscar")