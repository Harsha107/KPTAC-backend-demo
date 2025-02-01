from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import asyncpg
import bcrypt

app = FastAPI()

DATABASE_URL = "postgresql://postgres:123456789@localhost:5432/mydatabase"

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

class User(BaseModel):
    name: str
    email: str
    password: str

class LoginUser(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

@app.post("/register", response_model=dict)
async def register_user(user: User):
    db = await get_db()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    try:
        await db.execute("INSERT INTO users (name, email, password) VALUES ($1, $2, $3)",
                         user.name, user.email, hashed_password.decode('utf-8'))
        return {"message": "User created successfully"}
    except Exception:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        await db.close()

@app.post("/login", response_model=dict)
async def login_user(user: LoginUser):
    db = await get_db()
    record = await db.fetchrow("SELECT id, name, email, password FROM users WHERE email = $1", user.email)
    if record and bcrypt.checkpw(user.password.encode('utf-8'), record['password'].encode('utf-8')):
        return {"id": record["id"], "name": record["name"], "email": record["email"], "auth_token": "fake-jwt-token"}
    raise HTTPException(status_code=400, detail="Invalid email or password")
    await db.close()

@app.get("/users", response_model=List[UserResponse])
async def get_users():
    db = await get_db()
    users = await db.fetch("SELECT id, name, email FROM users")
    await db.close()
    return [dict(user) for user in users]

@app.get("/users/{user_id}")
async def get_user_by_id(user_id: int):
    db = await get_db()
    user = await db.fetchrow("SELECT id, name, email FROM users WHERE id = $1", user_id)
    await db.close()
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

class Post(BaseModel):
    title: str
    content: str
    user_id: int

class CreatePostResponse(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    created_at: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    user_id: int

@app.post("/posts", response_model=CreatePostResponse)
async def create_post(post: Post):
    db = await get_db()
    new_post = await db.fetchrow(
                "INSERT INTO posts (title, content, user_id) VALUES ($1, $2, $3) RETURNING id, title, content, user_id, created_at",
                                 post.title, post.content, post.user_id)
    await db.close()
    if new_post:
        return {**dict(new_post), "created_at": new_post["created_at"].isoformat()}
    raise HTTPException(status_code=500, detail="Failed to create a post")

@app.get("/posts", response_model=List[PostResponse])
async def get_posts():
    db = await get_db()
    posts = await db.fetch("SELECT id, title, content, user_id FROM posts")
    await db.close()
    return [dict(post) for post in posts]

@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post_by_id(post_id: int):
    db = await get_db()
    post = await db.fetchrow("SELECT id, title, content, user_id FROM posts WHERE id = $1", post_id)
    await db.close()
    if post:
        return PostResponse(**post)
    raise HTTPException(status_code=404, detail="Post not found")