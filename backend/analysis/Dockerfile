FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

ARG HF_TOKEN
ENV HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV HUGGING_FACE_HUB_TOKEN=

COPY handler.py analysis.py database.py ./

CMD ["handler.handler"]
