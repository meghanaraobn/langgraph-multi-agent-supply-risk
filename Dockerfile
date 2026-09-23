FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data

RUN pip install --no-cache-dir -e .

# chunking.py's NLTKTextSplitter needs punkt_tab's trained sentence-boundary
# model; baked into the image so ingestion never depends on outbound network
# access at runtime.
ENV NLTK_DATA=/usr/local/share/nltk_data
RUN python -m nltk.downloader -d "$NLTK_DATA" punkt_tab

EXPOSE 8000

CMD ["uvicorn", "supplyguard.main:app", "--host", "0.0.0.0", "--port", "8000"]
