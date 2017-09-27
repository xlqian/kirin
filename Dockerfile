FROM navitia/python

WORKDIR /usr/src/app

COPY . .

#we remove protobuf from the dependancy since it's already installed with c++ extension built in

RUN apk --update --no-cache add \
        g++ \
        build-base \
        python-dev \
        libstdc++ \
        git \
        postgresql-dev \
        postgresql-client \
        libpq && \
    sed -i -e '/protobuf/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn && \
    python setup.py build_version && \
    python setup.py build_pbf && \
    apk del \
        g++ \
        build-base \
        python-dev \
        zlib-dev \
        musl \
        musl-dev \
        postgresql-dev \
        git


ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=cpp
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2

CMD python ./manage.py db upgrade; gunicorn -b 0.0.0.0:9090 --access-logfile - kirin:app

