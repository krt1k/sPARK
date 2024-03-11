FROM python:3.10.13-slim-bullseye
COPY . /app
WORKDIR /app/web
RUN apt-get update && apt-get install -y sqlite3
RUN pip install -r /app/requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]