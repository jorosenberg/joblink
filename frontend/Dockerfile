FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py database.py selenium_scraper.py parser.py ./
COPY templates/ templates/

# Render injects PORT (10000); HF Space uses 7860 (README app_port);
# plain docker run keeps working via the default.
EXPOSE 7860
CMD gunicorn -b 0.0.0.0:${PORT:-7860} -w 2 --timeout 300 app:app
