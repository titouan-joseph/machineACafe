FROM python:3.8-slim

WORKDIR /bot

COPY ./requirements.txt .
RUN apt-get update \
    && apt-get upgrade gcc -y \
    && pip install --upgrade pip\
    && pip install -r requirements.txt \
    && rm requirements.txt \
    && mkdir /bot/database

COPY ./machineACafe.py .

CMD ["python", "machineACafe.py"]
