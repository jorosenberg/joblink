"""
HTTP shim - replaces the Lambda runtime for the analysis function.
POST / behaves like InvocationType='Event': returns 202 immediately and
runs handler.handler in a background thread.
Run: uvicorn server:app --host 0.0.0.0 --port 7860
"""
import threading

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handler import handler

app = FastAPI(title="joblink analysis")


@app.get("/")
def health():
    return {"status": "ok", "service": "joblink-analysis"}


@app.post("/")
async def analyze(request: Request):
    event = await request.json()
    threading.Thread(target=handler, args=(event, None), daemon=True).start()
    return JSONResponse({"message": "analysis started"}, status_code=202)


@app.post("/analyze")
async def analyze_alias(request: Request):
    return await analyze(request)
