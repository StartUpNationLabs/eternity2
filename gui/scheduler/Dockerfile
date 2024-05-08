FROM python:3.10-bookworm

COPY requirements.txt /scheduler/requirements.txt

RUN pip install -r /scheduler/requirements.txt

COPY . /scheduler

WORKDIR /scheduler

CMD ["python", "solve_eternity.py"]