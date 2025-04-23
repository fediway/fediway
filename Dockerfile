FROM python:3.10-slim

RUN apt-get update \
  && apt-get install -y openjdk-17-jre-headless curl \
  && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64
ENV PATH $JAVA_HOME/bin:$PATH

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_ENV=production

ENV APP_SECRET=
ENV APP_HOST=

ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_USER=mastodon
ENV DB_PASS=
ENV DB_NAME=mastodon_production

ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV REDIS_USER=postgres
ENV REDIS_PASS=

ENV IPV4_LOCATION_FILE=data/geo-whois-asn-country-ipv4.mmdb
ENV IPV6_LOCATION_FILE=data/geo-whois-asn-country-ipv6.mmdb

# Create non-root user and set up directories
RUN addgroup --system --gid 1001 fediway && \
    adduser --system --uid 1001 --gid 1001 --no-create-home fediway && \
    mkdir -p /app && \
    chown -R fediway:fediway /app

# Set work directory
WORKDIR /app

# copy requirements.txt
COPY --chown=fediway:fediway requirements.txt .

# install requirements
RUN pip install --no-cache-dir --upgrade torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# download jars (for spark)
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.3.0/spark-sql-kafka-0-10_2.12-3.3.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.1026/aws-java-sdk-bundle-1.11.1026.jar /opt/spark/jars/

ENV SPARK_CLASSPATH="/opt/spark/jars/*"

# download whois geolocation databases
ADD https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv4.mmdb data/geo-whois-asn-country-ipv4.mmdb
ADD https://cdn.jsdelivr.net/npm/@ip-location-db/geo-whois-asn-country-mmdb/geo-whois-asn-country-ipv6.mmdb data/geo-whois-asn-country-ipv6.mmdb

# Copy application code
COPY --chown=fediway:fediway . .

# Switch to fediway user
USER fediway

# run api
CMD ["fastapi", "run", "api/main.py"]