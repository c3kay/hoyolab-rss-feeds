FROM python:3.13-slim
LABEL authors="c3kay"

ARG version=0.0.1
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_HOYOLAB_RSS_FEEDS=$version

RUN mkdir /app /data
WORKDIR /app
VOLUME /data

COPY pyproject.toml /app/
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir .

COPY src/hoyolabrssfeeds /app/hoyolabrssfeeds
RUN echo '[genshin]\nfeed.json.path = "/data/genshin.json"' > /app/config.toml

ENTRYPOINT ["python3", "-m", "hoyolabrssfeeds"]
CMD ["-c", "/app/config.toml"]
