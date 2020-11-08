FROM python:3

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32

COPY sources.list /etc/apt/

RUN apt-get update
RUN apt-get install -y libgdal-dev g++ --no-install-recommends && \
    apt-get clean -y
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /usr/src/app

RUN pip install geopandas matplotlib tqdm pymongo

COPY . .

CMD [ "python", "save_geojson.py" ]