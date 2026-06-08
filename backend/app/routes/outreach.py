from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_conn
from app.routes.auth import get_current_user

router = APIRouter(prefix="/outreach", tags=["outreach"])


class CampaignCreate(BaseModel):
    name: str
    subject: str
    body: str


class SendRequest(BaseModel):
    campaign_id: int
    lead_ids: list[int]


@router.get("/campaigns")
def list_campaigns(user=Depends(get_current_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM outreach_campaigns WHERE user_id=? ORDER BY created_at DESC", (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/campaigns")
def create_campaign(req: CampaignCreate, user=Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO outreach_campaigns (user_id, name, subject, body) VALUES (?,?,?,?)",
            (user["id"], req.name, req.subject, req.body),
        )
    return {"id": cur.lastrowid, "message": "Campaign created"}


@router.post("/send")
def log_send(req: SendRequest, user=Depends(get_current_user)):
    """Log that emails were sent for a campaign (actual sending is done by email_sender.py)."""
    with get_conn() as conn:
        campaign = conn.execute(
            "SELECT id FROM outreach_campaigns WHERE id=? AND user_id=?",
            (req.campaign_id, user["id"]),
        ).fetchone()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        for lead_id in req.lead_ids:
            conn.execute(
                "INSERT INTO outreach_logs (campaign_id, lead_id) VALUES (?,?)",
                (req.campaign_id, lead_id),
            )
            conn.execute("UPDATE leads SET status='contacted' WHERE id=? AND user_id=?", (lead_id, user["id"]))
        conn.execute(
            "UPDATE outreach_campaigns SET sent_count=sent_count+? WHERE id=?",
            (len(req.lead_ids), req.campaign_id),
        )
    return {"message": f"Logged {len(req.lead_ids)} sends"}


@router.get("/campaigns/{campaign_id}/logs")
def campaign_logs(campaign_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        campaign = conn.execute(
            "SELECT id FROM outreach_campaigns WHERE id=? AND user_id=?",
            (campaign_id, user["id"]),
        ).fetchone()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        rows = conn.execute(
            """SELECT ol.*, l.business_name, l.email FROM outreach_logs ol
               JOIN leads l ON l.id=ol.lead_id
               WHERE ol.campaign_id=? ORDER BY ol.sent_at DESC""",
            (campaign_id,),
        ).fetchall()
    return [dict(r) for r in rows]
