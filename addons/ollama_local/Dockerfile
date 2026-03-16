ARG BUILD_FROM=ollama/ollama:latest
FROM ${BUILD_FROM}

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
