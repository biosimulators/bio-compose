FROM ghcr.io/biosimulators/bio-check-worker:latest

SHELL ["/usr/bin/env", "bash", "-c"]

ENV JUPYTER_TOKEN='' \
    JUPYTER_ENABLE_LAB=yes \
    GRANT_SUDO=yes

EXPOSE 8888

WORKDIR /app

COPY dockerfile-assets/requirements.image.txt /tmp/requirements.image.txt

RUN source ~/.bashrc  \
    && mkdir -p /opt/notebooks \
    && poetry run pip install -r /tmp/requirements.image.txt

CMD ["bash", "-c", "source ~/.bashrc && poetry run jupyter lab --ip='*' --port=8888 --allow-root --no-browser"]
