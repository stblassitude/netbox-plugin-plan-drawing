# Builds a NetBox image with this plugin installed, for local testing via docker-compose.yml
# at the root of the repository.
ARG NETBOX_IMAGE=netboxcommunity/netbox:v4.7

FROM ${NETBOX_IMAGE}

# Building the package unpacks the bundled draw.io into the plugin's static files. The
# download is skipped if the build context already contains an unpacked copy, or a cached
# download in .cache/drawio/.
COPY . /source/netbox-plugin-plan-drawing
RUN /usr/local/bin/uv pip install --no-cache /source/netbox-plugin-plan-drawing \
    && rm -rf /source/netbox-plugin-plan-drawing

COPY docker/plugins.py /etc/netbox/config/plugins.py

RUN SECRET_KEY="dummydummydummydummydummydummydummydummydummydummy" \
    python /opt/netbox/netbox/manage.py collectstatic --no-input --no-color
