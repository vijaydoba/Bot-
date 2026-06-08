from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.models.database import init_db
from app.routes import auth, chatbots, leads, chat, outreach
import os

app = FastAPI(title="AI Chatbot SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(auth.router)
app.include_router(chatbots.router)
app.include_router(leads.router)
app.include_router(chat.router)
app.include_router(outreach.router)


_WIDGET_PATH = os.getenv("WIDGET_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "chatbot"))
if os.path.isdir(_WIDGET_PATH):
    app.mount("/static", StaticFiles(directory=_WIDGET_PATH), name="static")


@app.get("/")
def root():
    return {"status": "ok", "message": "AI Chatbot SaaS API running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/demo/{chatbot_id}", response_class=HTMLResponse)
def demo(chatbot_id: int):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Chatbot Demo</title>
  <style>
    body {{ margin: 0; font-family: sans-serif; background: #f3f4f6;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; flex-direction: column; gap: 16px; }}
    .card {{ background: #fff; border-radius: 16px; padding: 40px;
             box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; max-width: 480px; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; color: #111; }}
    p {{ color: #6b7280; margin: 0; }}
    .badge {{ display:inline-block; margin-top:16px; background:#ecfdf5;
              color:#059669; border-radius:999px; padding:4px 14px; font-size:13px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Your AI Chatbot is Live</h1>
    <p>Click the chat bubble in the bottom-right corner to start talking to your bot.</p>
    <div class="badge">Powered by Claude AI</div>
  </div>
  <script>
    window.AIChatbotId = {chatbot_id};
    window.AIChatbotApiUrl = "http://localhost:8000";
  </script>
  <script src="http://localhost:8000/static/widget.js"></script>
</body>
</html>"""
