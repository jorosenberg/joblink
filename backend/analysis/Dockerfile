FROM public.ecr.aws/lambda/python:3.11

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp

COPY package/ ${LAMBDA_TASK_ROOT}/

ARG HF_TOKEN
ENV HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HUGGING_FACE_HUB_TOKEN=

COPY handler.py analysis.py database.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
