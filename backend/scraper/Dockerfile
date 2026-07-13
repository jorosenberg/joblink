# Render free web service (Docker) - replaces the AWS Lambda container image.
# handler.py logic unchanged; self-invokes run as threads (SERVER_MODE=1),
# analysis via ANALYSIS_URL. Build context: ./backend
FROM python:3.11-slim
WORKDIR /app
ENV SERVER_MODE=1
COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/database.py scraper/handler.py scraper/scraper.py scraper/parser.py scraper/server.py ./
EXPOSE 7860
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}
