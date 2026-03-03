FROM public.ecr.aws/lambda/python:3.11

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp

COPY analysis/requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

ARG HF_TOKEN
ENV HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HUGGING_FACE_HUB_TOKEN=

COPY shared/database.py analysis/handler.py analysis/analysis.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
