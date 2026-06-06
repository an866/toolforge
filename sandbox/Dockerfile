FROM python:3.12-slim

RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    pandas \
    pillow \
    lxml \
    openpyxl \
    python-docx \
    PyPDF2

RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
