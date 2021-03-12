from jinja2 import Template
import logging
import ops.charm
import ops.model
import ops.framework
from . import templates


try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources
class SquidCluster(ops.framework.Object):
    """Peer relation object for Squid"""

    relation_name: str = None
    log: logging.Logger = None

    def __init__(self, charm: ops.charm.CharmBase, relation_name: str):
        super().__init__(charm, relation_name)

        self.relation = self.framework.model.get_relation(relation_name)
        self.log = logging.getLogger("squid.{}".format(relation_name))

        self.framework.observe(
            charm.on[relation_name].relation_changed, self._on_changed
        )
        self.framework.observe(charm.on[relation_name].relation_broken, self._on_broken)

    def add_url(self, url: str):
        if self.framework.model.unit.is_leader():
            allowed_urls = self.allowed_urls
            allowed_urls.add(url)
            self.update_allowed_urls(allowed_urls)
            self.framework.model.unit.status = ops.model.ActiveStatus(
                repr(self.allowed_urls)
            )

    def delete_url(self, url: str):
        if self.framework.model.unit.is_leader():
            allowed_urls = self.allowed_urls
            self.framework.model.unit.status = ops.model.ActiveStatus(self.allowed_urls)
            if url in allowed_urls:
                allowed_urls.remove(url)
                self.update_allowed_urls(allowed_urls)

    def _on_changed(self, event):
        self.log.debug(f"on_changed: {self.framework.model.unit.name}")

    def _on_broken(self, event):
        self.log.debug(f"on_broken: {self.framework.model.unit.name}")

    @property
    def squid_config(self):
        allowed_urls_string = self._generate_allowedurls_config(self.allowed_urls)
        squid_config_template = pkg_resources.read_text(templates, "squid.conf")
        return Template(squid_config_template).render(allowed_urls=allowed_urls_string)

    @property
    def allowed_urls(self):
        return eval(
            self.relation.data[self.framework.model.app].get(
                "allowed_urls", repr(set())
            )
        )

    def update_allowed_urls(self, allowed_urls: set):
        self.relation.data[self.framework.model.app]["allowed_urls"] = repr(
            allowed_urls
        )

    def is_ready(self):
        return self.relation is not None

    def _generate_allowedurls_config(self, allowed_urls: set):
        allowed_urls_text = ""
        for url in allowed_urls:
            allowed_urls_text += f"acl allowedurls dstdomain .{url}\n"
        if allowed_urls:
            allowed_urls_text += "http_access allow allowedurls\n"
        return allowed_urls_text
