
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

users_db = {}

SECRET_KEY = "CHAVE_SECRETA_FORTE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verificar_senha(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_senha(password):
    return pwd_context.hash(password)

def criar_token(dados: dict, expira_em_minutos: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = dados.copy()
    expire = datetime.utcnow() + timedelta(minutes=expira_em_minutos)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obter_usuario(username: str):
    return users_db.get(username)

def autenticar_usuario(username: str, senha: str):
    user = obter_usuario(username)
    if not user or not verificar_senha(senha, user["senha"]):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return obter_usuario(username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.post("/registro")
def registrar_usuario(form: OAuth2PasswordRequestForm = Depends()):
    if form.username in users_db:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    users_db[form.username] = {"username": form.username, "senha": hash_senha(form.password)}
    return {"msg": "Usuário registrado com sucesso"}

@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = autenticar_usuario(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    token = criar_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def usuario_atual(usuario: dict = Depends(get_current_user)):
    return {"usuario": usuario["username"]}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
