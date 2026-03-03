FROM public.ecr.aws/lambda/python:3.11

ENV JOBLIB_TEMP_FOLDER=/tmp
ENV MPLCONFIGDIR=/tmp

COPY package/ ${LAMBDA_TASK_ROOT}/
COPY handler.py database.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
