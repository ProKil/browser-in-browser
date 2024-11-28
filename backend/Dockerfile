FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
RUN pip install uv
COPY . .
RUN uv run playwright install --with-deps
CMD uv run python main.py $PORT