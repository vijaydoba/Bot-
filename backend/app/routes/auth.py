from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from app.models.database import get_conn
from app.utils.auth import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(req: RegisterRequest):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        trial_ends = (datetime.utcnow() + timedelta(days=14)).isoformat()
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, plan, trial_ends_at) VALUES (?,?,?,?,?)",
            (req.name, req.email, hash_password(req.password), "trial", trial_ends),
        )
        user_id = cur.lastrowid
    token = create_token(user_id, req.email)
    return {"token": token, "message": "Account created. 14-day trial started."}


@router.post("/login")
def login(req: LoginRequest):
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["id"], user["email"])
    return {"token": token, "name": user["name"], "plan": user["plan"]}


def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
        payload = decode_token(token)
        return {"id": int(payload["sub"]), "email": payload["email"]}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
