from django.db.models import Q
from utilities.querysets import RestrictedQuerySet

from .constants import PTR_ZONE_SUFFIXES


class EnabledQuerySet(RestrictedQuerySet):
    def enabled(self):
        return self.filter(enabled=True)


class ZoneQuerySet(EnabledQuerySet):
    def _gen_q(self):
        q = Q()
        for s in PTR_ZONE_SUFFIXES:
            q |= Q(name__endswith=s)
        return q

    def forward(self):
        return self.exclude(self._gen_q())

    def reverse(self):
        return self.filter(self._gen_q())
