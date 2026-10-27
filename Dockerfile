FROM odoo:19.0

USER root

# Copy configuration
COPY config/odoo.conf /etc/odoo/odoo.conf

# Copy custom addons
COPY custom_addons /mnt/extra-addons

# Ensure correct permissions
RUN chown -R odoo:odoo /etc/odoo /mnt/extra-addons

USER odoo
