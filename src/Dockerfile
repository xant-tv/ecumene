# ======
# CLIENT
# Install necessary Oracle dependencies
# ======
FROM ubuntu:18.04 AS client

ENV ORACLE_ZIP_INTERNAL_FOLDER=instantclient_21_5
ENV CLIENT_ZIP=oracleinstantclient.zip

# Oracle client dependencies
WORKDIR /root
RUN apt-get update && apt-get -yq install unzip wget
RUN wget -O oracleinstantclient.zip https://download.oracle.com/otn_software/linux/instantclient/215000/instantclient-basic-linux.x64-21.5.0.0.0dbru.zip
RUN unzip ${CLIENT_ZIP}
RUN mv ${ORACLE_ZIP_INTERNAL_FOLDER} oracle

# ======
# BUILDER
# Set up python environment and web server
# ======
FROM python:3.8 as builder

# Application setup
ENV APP_HOME /app
WORKDIR $APP_HOME

# Set python environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Oracle home setup
ENV ORACLE_HOME /opt/oracle
ENV TNS_ADMIN ${ORACLE_HOME}/network/admin
VOLUME ["${TNS_ADMIN}"]

# Expose local port that application will bind to
EXPOSE 8080

# Oracle client from previous stage
COPY --from=client /root/oracle ${ORACLE_HOME}
RUN apt-get update \
    && apt-get -yq install libaio1 \
    && apt-get -yq autoremove \
    && apt-get clean \
    && echo ${ORACLE_HOME} > /etc/ld.so.conf.d/oracle.conf \
    && mkdir -p ${TNS_ADMIN} \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install pipenv
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends gcc build-essential libaio1
RUN pip install pipenv

# Install python dependencies to system
COPY . .
RUN pipenv install && pipenv install --system

# User setup
RUN groupadd -r ecumene \
    && useradd -r -g ecumene ecumene \
    && chown -R ecumene:ecumene .
USER ecumene:ecumene

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]