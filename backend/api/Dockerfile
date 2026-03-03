FROM public.ecr.aws/lambda/python:3.11

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp

COPY api/package/ ${LAMBDA_TASK_ROOT}/
COPY shared/database.py api/handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
