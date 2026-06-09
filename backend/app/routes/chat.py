import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_conn

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    chatbot_id: int
    message: str
    session_id: Optional[str] = None


def _get_history(chatbot_id: int, session_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT visitor_message, bot_response FROM conversations
               WHERE chatbot_id=? AND session_id=?
               ORDER BY created_at ASC LIMIT 20""",
            (chatbot_id, session_id),
        ).fetchall()
    messages = []
    for h in rows:
        if h["visitor_message"]:
            messages.append({"role": "user", "content": h["visitor_message"]})
        if h["bot_response"]:
            messages.append({"role": "assistant", "content": h["bot_response"]})
    return messages


def _reply_groq(system_prompt: str, messages: list) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
        messages=[{"role": "system", "content": system_prompt}] + messages,
    )
    return response.choices[0].message.content


def _reply_anthropic(system_prompt: str, messages: list) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


@router.post("/")
def chat(req: ChatRequest):
    with get_conn() as conn:
        bot = conn.execute(
            "SELECT * FROM chatbots WHERE id=? AND is_active=1", (req.chatbot_id,)
        ).fetchone()
    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot not found or inactive")

    session_id = req.session_id or str(uuid.uuid4())
    messages = _get_history(req.chatbot_id, session_id)
    messages.append({"role": "user", "content": req.message})

    provider = (bot["provider"] or "groq").lower()
    if provider == "anthropic":
        reply = _reply_anthropic(bot["system_prompt"], messages)
    else:
        reply = _reply_groq(bot["system_prompt"], messages)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (chatbot_id, session_id, visitor_message, bot_response) VALUES (?,?,?,?)",
            (req.chatbot_id, session_id, req.message, reply),
        )

    return {"reply": reply, "session_id": session_id}


@router.get("/history/{chatbot_id}/{session_id}")
def get_history(chatbot_id: int, session_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT visitor_message, bot_response, created_at
               FROM conversations WHERE chatbot_id=? AND session_id=?
               ORDER BY created_at ASC""",
            (chatbot_id, session_id),
        ).fetchall()
    return [dict(r) for r in rows]
