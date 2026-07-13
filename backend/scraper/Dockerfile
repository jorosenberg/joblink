# Hugging Face Space (Docker SDK) - replaces the AWS Lambda container image
# (was: public.ecr.aws/lambda/python:3.11). handler.py logic unchanged;
# self-invokes run as threads (SERVER_MODE=1), analysis via ANALYSIS_URL.
# Space repo layout (flat): Dockerfile, requirements.txt, database.py,
# handler.py, scraper.py, parser.py, server.py
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app
ENV SERVER_MODE=1

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user *.py ./

EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
