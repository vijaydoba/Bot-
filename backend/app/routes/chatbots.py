from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_conn
from app.routes.auth import get_current_user

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


class ChatbotCreate(BaseModel):
    business_name: str
    business_type: Optional[str] = None
    system_prompt: Optional[str] = None
    widget_color: Optional[str] = "#4F46E5"
    welcome_message: Optional[str] = "Hi! How can I help you today?"
    provider: Optional[str] = "groq"


class ChatbotUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    system_prompt: Optional[str] = None
    widget_color: Optional[str] = None
    welcome_message: Optional[str] = None
    provider: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
def list_chatbots(user=Depends(get_current_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chatbots WHERE user_id=? ORDER BY created_at DESC", (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/")
def create_chatbot(req: ChatbotCreate, user=Depends(get_current_user)):
    default_prompt = (
        f"You are a helpful assistant for {req.business_name}. "
        f"Answer customer questions about our services, hours, pricing, and bookings. "
        f"Be friendly, concise, and professional. If you don't know something, offer to connect them with a human."
    )
    prompt = req.system_prompt or default_prompt
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chatbots (user_id, business_name, business_type, system_prompt, widget_color, welcome_message, provider) VALUES (?,?,?,?,?,?,?)",
            (user["id"], req.business_name, req.business_type, prompt, req.widget_color, req.welcome_message, req.provider or "groq"),
        )
        bot_id = cur.lastrowid
    return {"id": bot_id, "message": "Chatbot created successfully"}


@router.get("/public/{bot_id}")
def get_chatbot_public(bot_id: int):
    """Public endpoint used by the chat widget to load bot name, color and welcome message."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, business_name, widget_color, welcome_message FROM chatbots WHERE id=? AND is_active=1",
            (bot_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return dict(row)


@router.get("/{bot_id}")
def get_chatbot(bot_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM chatbots WHERE id=? AND user_id=?", (bot_id, user["id"])
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return dict(row)


@router.put("/{bot_id}")
def update_chatbot(bot_id: int, req: ChatbotUpdate, user=Depends(get_current_user)):
    fields, values = [], []
    for field, val in req.dict(exclude_none=True).items():
        fields.append(f"{field}=?")
        values.append(int(val) if isinstance(val, bool) else val)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    values += [bot_id, user["id"]]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE chatbots SET {', '.join(fields)} WHERE id=? AND user_id=?", values
        )
    return {"message": "Updated"}


@router.delete("/{bot_id}")
def delete_chatbot(bot_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        conn.execute("DELETE FROM chatbots WHERE id=? AND user_id=?", (bot_id, user["id"]))
    return {"message": "Deleted"}


@router.get("/{bot_id}/stats")
def chatbot_stats(bot_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        bot = conn.execute(
            "SELECT id FROM chatbots WHERE id=? AND user_id=?", (bot_id, user["id"])
        ).fetchone()
        if not bot:
            raise HTTPException(status_code=404, detail="Chatbot not found")
        total = conn.execute(
            "SELECT COUNT(*) as c FROM conversations WHERE chatbot_id=?", (bot_id,)
        ).fetchone()["c"]
        today = conn.execute(
            "SELECT COUNT(*) as c FROM conversations WHERE chatbot_id=? AND date(created_at)=date('now')",
            (bot_id,),
        ).fetchone()["c"]
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) as c FROM conversations WHERE chatbot_id=?", (bot_id,)
        ).fetchone()["c"]
    return {"total_messages": total, "messages_today": today, "unique_sessions": sessions}
