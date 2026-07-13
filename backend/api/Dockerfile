# Hugging Face Space (Docker SDK) - replaces the AWS Lambda container image
# (was: public.ecr.aws/lambda/python:3.11). handler.py unchanged; server.py
# converts HTTP <-> Lambda-event exactly like API Gateway AWS_PROXY did.
# Space repo layout (flat): Dockerfile, requirements.txt, database.py,
# handler.py, server.py  (assembled by deploy/hf_stage.sh)
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user *.py ./

EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
