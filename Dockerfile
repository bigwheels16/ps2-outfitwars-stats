ARG PYTHON_VERSION=3.9.1

FROM python:${PYTHON_VERSION}
ARG PYTHON_VERSION
RUN echo "Building with Python version $PYTHON_VERSION"

RUN useradd -m -u 1000 user
EXPOSE 8080

WORKDIR /app
ENV PYTHONPATH="/app/src:${PYTHONPATH}"

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY . /app
RUN chown 1000:1000 -R /app

# Security context in k8s requires uid as user
USER 1000

CMD ["python", "src/bootstrap.py"]
