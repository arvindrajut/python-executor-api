FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc g++ make curl git flex bison \
    libcap-dev libprotobuf-dev protobuf-compiler \
    libnl-3-dev libnl-route-3-dev \
    pkg-config zlib1g-dev libncurses-dev libtool automake \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/google/nsjail.git /opt/nsjail && \
    cd /opt/nsjail && \
    make && \
    cp nsjail /usr/bin/nsjail

RUN mkdir -p /sandbox && chmod 777 /sandbox

WORKDIR /app
COPY main.py /app/

RUN pip install flask pandas numpy

EXPOSE 8080
CMD ["python", "main.py"]