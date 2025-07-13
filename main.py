
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Configuração de ambiente
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
SECRET_KEY = os.getenv("SECRET_KEY", "CHAVE_SUPER_SECRETA")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Banco de dados
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    senha_hash = Column(String)

class Favorito(Base):
    __tablename__ = "favoritos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    nome = Column(String)
    preco = Column(String)
    link = Column(String)

class Alerta(Base):
    __tablename__ = "alertas"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    produto = Column(String)
    preco_alvo = Column(String)

# FastAPI e CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_senha(password):
    return pwd_context.hash(password)

def verificar_senha(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def criar_token(data: dict, expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def autenticar_usuario(db: Session, username: str, senha: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verificar_senha(senha, user.senha_hash):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.post("/registro")
def registrar_usuario(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == form.username).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    novo = User(username=form.username, senha_hash=hash_senha(form.password))
    db.add(novo)
    db.commit()
    return {"msg": "Usuário criado com sucesso"}

@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = autenticar_usuario(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    token = criar_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def usuario_atual(user: User = Depends(get_current_user)):
    return {"usuario": user.username}

@app.get("/")
def raiz():
    return {"status": "API está rodando!"}


from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy.orm import Session

@app.post("/alerta")
def criar_alerta(produto: str, preco_alvo: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerta = Alerta(user_id=user.id, produto=produto, preco_alvo=preco_alvo)
    db.add(alerta)
    db.commit()

    # Enviar e-mail simulando alerta imediato
    if "SENDGRID_API_KEY" in os.environ:
        try:
            message = Mail(
                from_email="alerta@suaapp.com",
                to_emails=user.username,  # deve ser um e-mail válido
                subject=f"📉 Alerta de preço criado para {produto}",
                html_content=f"<p>Você será notificado quando o preço cair abaixo de <strong>{preco_alvo}</strong>.</p>"
            )
            sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
            sg.send(message)
        except Exception as e:
            print("Erro ao enviar email:", e)

    return {"msg": f"Alerta criado para {produto} com alvo R$ {preco_alvo}"}


import requests

@app.get("/verificar-alertas")
def verificar_alertas(db: Session = Depends(get_db)):
    alertas = db.query(Alerta).all()
    enviados = []

    for alerta in alertas:
        # Buscar produto no Mercado Livre
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={alerta.produto}&limit=1"
        res = requests.get(url)
        if res.status_code != 200:
            continue
        resultados = res.json().get("results", [])
        if not resultados:
            continue
        preco_atual = float(resultados[0]["price"])
        preco_desejado = float(alerta.preco_alvo.replace(",", ".").replace("R$", "").strip())

        if preco_atual <= preco_desejado:
            # Enviar email
            try:
                if "SENDGRID_API_KEY" in os.environ:
                    user = db.query(User).filter(User.id == alerta.user_id).first()
                    message = Mail(
                        from_email="alerta@suaapp.com",
                        to_emails=user.username,
                        subject=f"📉 Oferta encontrada: {alerta.produto}",
                        html_content=f"<p>O produto <strong>{alerta.produto}</strong> está por <strong>R$ {preco_atual:.2f}</strong> (abaixo de R$ {preco_desejado:.2f}).</p><p><a href='{resultados[0]['permalink']}'>Ver no Mercado Livre</a></p>"
                    )
                    sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
                    sg.send(message)
                    enviados.append(alerta.produto)
            except Exception as e:
                print("Erro ao enviar alerta:", e)

    return {"alertas_enviados": enviados}


@app.get("/me/alertas")
def listar_alertas(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alertas = db.query(Alerta).filter(Alerta.user_id == user.id).all()
    return [{"id": a.id, "produto": a.produto, "preco_alvo": a.preco_alvo} for a in alertas]

@app.delete("/me/alertas/{id}")
def deletar_alerta(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerta = db.query(Alerta).filter(Alerta.id == id, Alerta.user_id == user.id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    db.delete(alerta)
    db.commit()
    return {"msg": "Alerta removido com sucesso"}

@app.post("/me/favoritos")
def adicionar_favorito(produto: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorito = Favorito(user_id=user.id, nome=produto, link="", preco="")
    db.add(favorito)
    db.commit()
    return {"msg": f"{produto} adicionado aos favoritos"}

@app.get("/me/favoritos")
def listar_favoritos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favoritos = db.query(Favorito).filter(Favorito.user_id == user.id).all()
    return [{"id": f.id, "nome": f.nome} for f in favoritos]

@app.delete("/me/favoritos/{id}")
def deletar_favorito(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fav = db.query(Favorito).filter(Favorito.id == id, Favorito.user_id == user.id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorito não encontrado")
    db.delete(fav)
    db.commit()
    return {"msg": "Favorito removido com sucesso"}

@app.get("/me/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_alertas = db.query(Alerta).filter(Alerta.user_id == user.id).count()
    total_favoritos = db.query(Favorito).filter(Favorito.user_id == user.id).count()
    ultimo_alerta = db.query(Alerta).filter(Alerta.user_id == user.id).order_by(Alerta.id.desc()).first()
    produto_freq = db.query(Alerta.produto).filter(Alerta.user_id == user.id).all()
    contagem_produtos = {}
    for p in produto_freq:
        contagem_produtos[p[0]] = contagem_produtos.get(p[0], 0) + 1

    return {
        "total_alertas": total_alertas,
        "total_favoritos": total_favoritos,
        "ultimo_alerta": {
            "produto": ultimo_alerta.produto,
            "preco": ultimo_alerta.preco_alvo
        } if ultimo_alerta else None,
        "produtos_mais_monitorados": contagem_produtos
    }

from routers import amazon_scraper
app.include_router(amazon_scraper.router)

# Inicialização
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
