from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
import time

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Banco de usuários em memória (usar DB real depois)
fake_users_db = {}

SECRET_KEY = "CHAVE_SECRETA_SUPERSEGURA"

class User(BaseModel):
    email: str
    password: str

def create_token(email: str):
    payload = {
        "sub": email,
        "exp": time.time() + 3600
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

@router.post("/register")
def register(user: User):
    if user.email in fake_users_db:
        raise HTTPException(status_code=400, detail="Usuário já registrado")
    hashed = pwd_context.hash(user.password)
    fake_users_db[user.email] = hashed
    return {"msg": "Registrado com sucesso"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password
    hashed = fake_users_db.get(email)
    if not hashed or not pwd_context.verify(password, hashed):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(email)
    return {"access_token": token, "token_type": "bearer"}