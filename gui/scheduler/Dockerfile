FROM python:3.10-bookworm

COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

COPY . /app

WORKDIR /app

CMD ["python", "solve_eternity.py"]