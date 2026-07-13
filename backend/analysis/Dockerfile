# Hugging Face Space (Docker SDK) - replaces the AWS Lambda container image
# (was: public.ecr.aws/lambda/python:3.11). Same model (all-MiniLM-L6-v2)
# pre-downloaded at build; handler.py unchanged; POST / == Event invoke.
# Space repo layout (flat): Dockerfile, requirements.txt, database.py,
# handler.py, analysis.py, server.py
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp
ENV HF_HOME=/app/hf_cache

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --user --only-binary=:all: -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

COPY --chown=user *.py ./

EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
