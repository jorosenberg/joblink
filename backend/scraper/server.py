"""
HTTP shim - replaces AWS API Gateway (AWS_PROXY v2) + Lambda runtime.
handler.handler is called unchanged. SERVER_MODE=1 makes the handler's
self-invocations run as daemon threads (same semantics as Lambda Event).
Run: uvicorn server:app --host 0.0.0.0 --port 7860
"""
import os

os.environ.setdefault("SERVER_MODE", "1")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from handler import handler

app = FastAPI(title="joblink scraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Scrape-Password"],
    max_age=3600,
)


@app.get("/")
def health():
    return {"status": "ok", "service": "joblink-scraper"}


@app.post("/api/scrape")
async def scrape(request: Request):
    event = {"body": (await request.body()).decode("utf-8") or "{}"}
    result = handler(event, None)
    return Response(
        content=result.get("body", "{}"),
        status_code=result.get("statusCode", 200),
        media_type="application/json",
    )
