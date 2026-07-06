FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-venv python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/IEI_claude_using_analysis

RUN python3 -m venv /opt/IEI_claude_using_analysis/venv && \
    /opt/IEI_claude_using_analysis/venv/bin/pip install --upgrade pip

COPY backend/requirements.txt requirements.txt
RUN /opt/IEI_claude_using_analysis/venv/bin/pip install -r requirements.txt

COPY run.py cron_import.py db_process.py openai_process.py openai_import.py ./
COPY config.toml .
COPY backend backend

CMD ["/opt/IEI_claude_using_analysis/venv/bin/gunicorn", \
     "-w", "2", "-b", "0.0.0.0:5000", "run:app"]
