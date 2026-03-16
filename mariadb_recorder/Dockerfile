ARG BUILD_FROM=ghcr.io/home-assistant/{arch}-base:3.20
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-eo", "pipefail", "-c"]

RUN apk add --no-cache \
    bash \
    mariadb \
    mariadb-client \
    mariadb-server-utils \
    python3 \
    tzdata

COPY run.sh /run.sh
COPY init_internal.sh /init_internal.sh
COPY scripts/lib.sh /scripts/lib.sh

RUN chmod a+x /run.sh /init_internal.sh /scripts/lib.sh

CMD [ "/run.sh" ]
