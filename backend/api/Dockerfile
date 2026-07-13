# Render free web service (Docker) - replaces the AWS Lambda container image.
# handler.py unchanged; server.py converts HTTP <-> Lambda-event exactly like
# API Gateway AWS_PROXY did. Build context: ./backend
FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/database.py api/handler.py api/server.py ./
EXPOSE 7860
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}
