from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_conn
from app.routes.auth import get_current_user

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreate(BaseModel):
    business_name: str
    business_type: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@router.get("/")
def list_leads(
    status: Optional[str] = Query(None),
    business_type: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    query = "SELECT * FROM leads WHERE user_id=?"
    params = [user["id"]]
    if status:
        query += " AND status=?"
        params.append(status)
    if business_type:
        query += " AND business_type=?"
        params.append(business_type)
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city}%")
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.post("/")
def create_lead(req: LeadCreate, user=Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO leads
               (user_id, business_name, business_type, contact_name, email, phone, website, address, city, source, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user["id"], req.business_name, req.business_type, req.contact_name,
             req.email, req.phone, req.website, req.address, req.city, req.source, req.notes),
        )
    return {"id": cur.lastrowid, "message": "Lead added"}


@router.post("/bulk")
def bulk_import(leads: list[LeadCreate], user=Depends(get_current_user)):
    with get_conn() as conn:
        for lead in leads:
            conn.execute(
                """INSERT INTO leads
                   (user_id, business_name, business_type, contact_name, email, phone, website, address, city, source, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (user["id"], lead.business_name, lead.business_type, lead.contact_name,
                 lead.email, lead.phone, lead.website, lead.address, lead.city, lead.source, lead.notes),
            )
    return {"message": f"Imported {len(leads)} leads"}


@router.put("/{lead_id}")
def update_lead(lead_id: int, req: LeadUpdate, user=Depends(get_current_user)):
    fields, values = [], []
    for field, val in req.dict(exclude_none=True).items():
        fields.append(f"{field}=?")
        values.append(val)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    values += [lead_id, user["id"]]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE leads SET {', '.join(fields)} WHERE id=? AND user_id=?", values
        )
    return {"message": "Updated"}


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id=? AND user_id=?", (lead_id, user["id"]))
    return {"message": "Deleted"}


class VisitorCapture(BaseModel):
    chatbot_id: int
    session_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@router.post("/capture")
def capture_visitor_lead(req: VisitorCapture):
    """Public endpoint — no auth. Called by the chat widget when a visitor submits their contact info."""
    with get_conn() as conn:
        bot = conn.execute(
            "SELECT user_id, business_name, business_type FROM chatbots WHERE id=?",
            (req.chatbot_id,),
        ).fetchone()
        if not bot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        cur = conn.execute(
            """INSERT INTO leads
               (user_id, business_name, business_type, contact_name, email, phone, source, status, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                bot["user_id"], bot["business_name"], bot["business_type"],
                req.name, req.email, req.phone,
                "chatbot_widget", "new",
                f"Captured via chat widget. Session: {req.session_id}",
            ),
        )
    return {"id": cur.lastrowid, "message": "Thanks! We'll be in touch shortly."}


@router.get("/stats/summary")
def leads_summary(user=Depends(get_current_user)):
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM leads WHERE user_id=?", (user["id"],)).fetchone()["c"]
        by_status = conn.execute(
            "SELECT status, COUNT(*) as c FROM leads WHERE user_id=? GROUP BY status", (user["id"],)
        ).fetchall()
        by_type = conn.execute(
            "SELECT business_type, COUNT(*) as c FROM leads WHERE user_id=? GROUP BY business_type", (user["id"],)
        ).fetchall()
    return {
        "total": total,
        "by_status": {r["status"]: r["c"] for r in by_status},
        "by_type": {r["business_type"]: r["c"] for r in by_type},
    }
