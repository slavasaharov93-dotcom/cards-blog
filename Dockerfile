FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY build.py .
COPY serve.py .
COPY articles/ ./articles/
COPY assets/ ./assets/
COPY offers.json .
COPY add_images.py .
COPY apply_factcheck.py .

# Build static site
RUN python build.py

# Expose port
EXPOSE 8000

# Serve
CMD ["python", "serve.py", "8000"]
