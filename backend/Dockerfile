FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV SLOTFLASH_DB=/data/slotflash.db
EXPOSE 12200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "12200"]
