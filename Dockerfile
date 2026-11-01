FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
COPY configs ./configs
RUN pip install --no-deps .
ENV MPLCONFIGDIR=/tmp/matplotlib PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "airbnb_lab.cli"]
CMD ["run"]
