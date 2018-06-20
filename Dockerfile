FROM alpine:3.7

RUN \
  apk add --update --no-cache nrpe monitoring-plugins nrpe-plugin bash python curl && \
  curl -s https://gist.githubusercontent.com/micw/d7c0e34aee751e81c5aa952b29b8631b/raw/8d67835c09ed2d32a61a05b5e4f0e2451fd2f0d4/update_config.py \
    > /usr/local/bin/update_config.py && \
  chmod 0755 /usr/local/bin/update_config.py

ENV \
  ALLOWED_HOSTS=127.0.0.1 \
  NRPE_DEBUG=0

ADD checks/ /usr/lib/monitoring-plugins/
ADD nrpe.cfg /etc/nrpe.cfg
ADD docker_entrypoint.sh /usr/local/bin/docker_entrypoint.sh

CMD /usr/local/bin/docker_entrypoint.sh
