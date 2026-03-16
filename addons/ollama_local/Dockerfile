ARG BUILD_FROM=ollama/ollama:latest
FROM ${BUILD_FROM}

RUN if command -v apt-get >/dev/null 2>&1; then \
      apt-get update \
      && apt-get install -y --no-install-recommends jq curl ca-certificates \
      && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache jq curl ca-certificates; \
    else \
      echo "No supported package manager found in base image"; \
      exit 1; \
    fi

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
