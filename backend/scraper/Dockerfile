FROM public.ecr.aws/lambda/python:3.11

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp

COPY scraper/package/ ${LAMBDA_TASK_ROOT}/
COPY shared/database.py scraper/handler.py scraper/scraper.py scraper/parser.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
