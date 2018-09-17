FROM python:3.4-alpine

ADD . /app

WORKDIR /app/resume

RUN pip install -r ../requirements.txt

EXPOSE 80

CMD ["python3","app.py"]

