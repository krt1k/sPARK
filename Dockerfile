FROM python:3.10.13-slim-bullseye
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "./web/app.py"]