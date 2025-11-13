FROM python:3.11-alpine
WORKDIR /app

# Instalar dependencias del sistema para psutil
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
