FROM python:3.13-slim
LABEL authors="c3kay"

# basically ignore version of python package
# version will be set with docker tag and label
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_HOYOLAB_RSS_FEEDS=1.0.0

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
