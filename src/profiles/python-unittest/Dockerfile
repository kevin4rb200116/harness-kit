FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# El perfil no tiene dependencias externas. Si tu proyecto las necesita,
# añade aquí un `COPY requirements.txt` + `RUN pip install -r`.
CMD ["python3", "--version"]
