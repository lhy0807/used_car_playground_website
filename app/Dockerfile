FROM python:3.8

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32

COPY sources.list /etc/apt/

RUN apt-get update
RUN apt-get install -y libgdal-dev g++ --no-install-recommends && \
    apt-get clean -y
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /usr/src/app

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 5100

COPY run_gunicorn.sh .
RUN chmod +x ./run_gunicorn.sh

COPY . . 

CMD [ "sh", "run_gunicorn.sh" ]