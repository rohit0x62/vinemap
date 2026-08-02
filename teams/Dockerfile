FROM python:3.11-slim

WORKDIR /app

COPY engine /app/engine
COPY teams /app/teams

RUN pip install --no-cache-dir -e /app/engine && \
    pip install --no-cache-dir -r /app/teams/requirements.txt

ENV VINEMAP_TEAMS_DATA_DIR=/data
ENV PYTHONPATH=/app/engine:/app/teams

EXPOSE 7430

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7430", "--app-dir", "/app/teams"]
