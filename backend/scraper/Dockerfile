FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py scraper.py parser.py database.py ./

CMD ["handler.handler"]
