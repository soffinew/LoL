from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import crud
import auth
import websocket
from database import engine, SessionLocal

# Создание таблиц
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Зависимость для БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Аутентификация ===
@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    return {"access_token": auth.create_access_token(user.id), "token_type": "bearer"}

# === Профиль ===
@app.get("/profile/{user_id}", response_model=schemas.User)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user(db, user_id)

@app.put("/profile/{user_id}", response_model=schemas.User)
def update_profile(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    return crud.update_user(db, user_id, user_update)

@app.post("/upload/{user_id}")
def upload_photo(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return crud.save_photo(db, user_id, file)

# === Лайки ===
@app.post("/like/{from_id}/{to_id}")
def like(from_id: int, to_id: int, db: Session = Depends(get_db)):
    return crud.like_user(db, from_id, to_id)

# === Чат (WebSocket) ===
@app.websocket("/ws/{user_id}")
async def chat_endpoint(websocket: WebSocket, user_id: int):
    await websocket_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.send_message(user_id, data)
    except Exception as e:
        print(e)
        websocket_manager.disconnect(websocket, user_id)