ARG PYTHON_VERSION=3.6
FROM ubuntu:18.04 AS client
ARG MODULE

ENV ORACLE_ZIP_INTERNAL_FOLDER=instantclient_21_5
ENV CLIENT_ZIP=oracleinstantclient.zip
ENV SDK_ZIP=oraclesdk.zip

# Install Oracle Instant Client
WORKDIR /root
RUN apt-get update && apt-get -yq install unzip wget
RUN wget -O oracleinstantclient.zip https://download.oracle.com/otn_software/linux/instantclient/215000/instantclient-basic-linux.x64-21.5.0.0.0dbru.zip
RUN wget -O oraclesdk.zip https://download.oracle.com/otn_software/linux/instantclient/215000/instantclient-sdk-linux.x64-21.5.0.0.0dbru.zip
RUN unzip ${CLIENT_ZIP}
RUN unzip ${SDK_ZIP}
RUN mv ${ORACLE_ZIP_INTERNAL_FOLDER} oracle

FROM python:3.8 as builder
ARG MODULE

ENV HOME /root
ENV ORACLE_HOME /opt/oracle
ENV TNS_ADMIN ${ORACLE_HOME}/network/admin
VOLUME ["${TNS_ADMIN}"]

# Copy/Load Oracle Instant Client
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
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential libaio1

# Install python dependencies in /.venv
COPY Pipfile .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy
ENV PATH="/.venv/bin:$PATH"
ENV MODULE=$MODULE
COPY . .

ENTRYPOINT ["sh","-c","python main.py $MODULE"]