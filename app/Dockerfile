FROM python:3

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32

COPY sources.list /etc/apt/

RUN apt-get update
RUN apt-get install -y libgdal-dev g++ --no-install-recommends && \
    apt-get clean -y
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /usr/src/app

COPY requirements.txt .
COPY run_gunicorn.sh .

RUN pip install -r requirements.txt

EXPOSE 5100
RUN chmod +x ./run_gunicorn.sh

COPY . . 

CMD [ "sh", "run_gunicorn.sh" ]