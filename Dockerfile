FROM python:3.10.2

WORKDIR /app

COPY requirements.txt .


RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt

COPY . .


CMD ["/app/venv/bin/python", "telegram_bot_v2kaz_rus.py"]
