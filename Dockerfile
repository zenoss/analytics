FROM zenoss/wheel:py2-2

RUN <<EOT
apt-get -q update
DEBIAN_FRONTEND=noninteractive apt-get -q install --yes --no-install-recommends openjdk-21-jre-headless
EOT

USER zenoss

RUN <<EOT
python2 -m pip --no-python-version-warning --no-cache-dir install --index-url http://zenpip.zenoss.eng/simple --trusted-host zenpip.zenoss.eng --user "jsbuilder==2.0.0"
EOT

USER root
