# 1. Bazinio paveikslo pasirinkimas: Ubuntu 24.04 LTS
FROM ubuntu:24.04

# 2. Įdiegiame Python ir reikalingus sisteminius paketus
# Pridėta python3-pip ir build priklausomybės
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip \
    build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Darbo aplankas
WORKDIR /app

# 4. Priklausomybių kopijavimas
COPY requirements.txt .

# 5. PATAISYTA: Dabar naudojame pip3 vietoj pip
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# 6. Kodo kopijavimas ir statinių failų surinkimas
COPY . .
# PATAISYTA: Naudojame python3
RUN python3 manage.py collectstatic --noinput


# 7. Django/Gunicorn nustatymai
ENV PYTHONUNBUFFERED 1
EXPOSE 8000

# 8. Pakeista paleidimo komanda, kuri bus naudojama pagal nutylėjimą
CMD ["/usr/bin/python3", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "Nomoklis.asgi:application"]
# CMD ["/usr/bin/python3", "manage.py", "check"]