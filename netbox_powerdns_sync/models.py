from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from taggit.managers import TaggableManager
from core.models import Job
from dcim.models import DeviceRole, Interface
from ipam.models import IPAddress, FHRPGroup
from netbox.models import NetBoxModel
from extras.models import Tag
from virtualization.models import VMInterface

from .choices import NamingFgrpGroupChoices, NamingDeviceChoices, NamingIpChoices
from .constants import JOB_NAME_SYNC
from .querysets import EnabledQuerySet, ZoneQuerySet
from .utils import get_ip_host, make_canonical, is_reverse
from .validators import hostname_validator, zone_validator


__all__ = (
    "ApiServer",
    "Zone",
)


class ApiServer(NetBoxModel):
    name = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        unique=True,
    )
    description = models.CharField(
        max_length=200,
        blank=True
    )
    enabled = models.BooleanField(
        null=False,
        default=True,
    )
    api_url = models.URLField(
        verbose_name="API URL",
        help_text="Base URL to PowerDNS REST API",
        max_length=200,
        unique=True,
    )
    api_token = models.CharField(
        verbose_name="API Token",
        max_length=200,
    )

    objects = EnabledQuerySet.as_manager()

    clone_fields = (
        "name", "api_url", "api_token", "description", "enabled", "tags",
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "API Server"

    def get_absolute_url(self):
        return reverse("plugins:netbox_powerdns_sync:apiserver", args=[self.pk])

    def __str__(self):
        return self.name


class Zone(NetBoxModel):
    name = models.CharField(
        help_text="Domain name of zone. Must be fully qualified.",
        max_length=200,
        blank=False,
        null=False,
        unique=True,
        validators=[MinLengthValidator(3), hostname_validator, zone_validator],
    )
    description = models.CharField(
        max_length=200,
        blank=True
    )
    enabled = models.BooleanField(
        null=False,
        default=True,
    )
    api_servers = models.ManyToManyField(
        to=ApiServer,
        verbose_name="API Servers",
        related_name="zones",
    )
    is_default = models.BooleanField(
        help_text="This zone is to be used as default if no other zone matches.",
        null=False,
        default=False,
    )
    default_ttl = models.IntegerField(
        help_text="TTL to use for new records if not set by TTL custom field",
        verbose_name="Default TTL",
        default=3600,
    )
    match_ipaddress_tags = models.ManyToManyField(
        to=Tag,
        help_text="Use this zone for IP addresses with these tags",
        verbose_name="Match IP address tags",
        related_name="+",
        blank=True,
    )
    match_interface_tags = models.ManyToManyField(
        to=Tag,
        help_text="Use this zone for interfaces or VM interfaces with these tags",
        verbose_name="Match interface tags",
        related_name="+",
        blank=True,
    )
    match_device_tags = models.ManyToManyField(
        to=Tag,
        help_text="Use this zone for devices or VMs with these tags",
        verbose_name="Match device tags",
        related_name="+",
        blank=True,
    )
    match_fhrpgroup_tags = models.ManyToManyField(
        to=Tag,
        help_text="Use this zone for FHRP groups with these tags",
        verbose_name="Match FHRP tags",
        related_name="+",
        blank=True,
    )
    match_device_roles = models.ManyToManyField(
        to=DeviceRole,
        help_text="Use this zone for devices or VMs with these roles",
        verbose_name="Match device roles",
        related_name="+",
        blank=True,
    )
    match_interface_mgmt_only = models.BooleanField(
        default=False,
        verbose_name="Match management interfaces only",
        help_text="Use this zone only for addresses assigned to management interfaces (other criteria must match first)"
    )
    naming_ip_method = models.CharField(
        max_length=200,
        help_text="How to construct DNS name from IP address",
        verbose_name="IP naming method",
        choices=NamingIpChoices,
        default=None,
        null=True,
    )
    naming_device_method = models.CharField(
        max_length=200,
        help_text="How to construct DNS name from device IP is assigned to",
        verbose_name="Device naming method",
        choices=NamingDeviceChoices,
        default=None,
        null=True,
    )
    naming_fgrpgroup_method = models.CharField(
        max_length=200,
        help_text="How to construct DNS name from FHRP Group IP is assigned to",
        verbose_name="FHRP Group naming method",
        choices=NamingFgrpGroupChoices,
        default=None,
        null=True,
    )
    # netbox-plugin-dns also has Zone model
    # if both plugins are installed, django complains:
    #   netbox_dns.Zone.tags: (fields.E304) Reverse accessor 'Tag.zone_set'
    #   for 'netbox_dns.Zone.tags' clashes with reverse accessor for
    #   'netbox_powerdns_sync.Zone.tags'
    # So let's disable generating reverse relation here.
    tags = TaggableManager(
        through="extras.TaggedItem",
        related_name="+"
    )

    @property
    def is_reverse(self) -> bool:
        if not self.name:
            return False
        return is_reverse(self.name)

    objects = ZoneQuerySet.as_manager()

    def clean_fields(self, exclude=None):
        if self.is_reverse and self.is_default:
            msg = "Reverse zone cannot be set as default"
            if exclude and "is_default" in exclude:
                raise ValidationError(msg)
            else:
                raise ValidationError({"is_default": msg})
        
        if not any((self.naming_ip_method, self.naming_fgrpgroup_method, \
            self.naming_device_method)):
            raise ValidationError("At least one of naming methods must be set")

    def delete(self, *args, **kwargs):
        # delete any scheduled jobs fot this zone
        if self.pk:
            jobs = Job.objects.filter(
                object_type_id=ContentType.objects.get_for_model(self).pk,
                object_id=self.pk,
                status="scheduled",
                name=JOB_NAME_SYNC
            )
            jobs.delete()
        return super().delete(*args, **kwargs)

    @classmethod
    def get_best_zone(cls, name: str) -> "Zone|None":
        """ Get the longest matching zone for a given name """
        name = make_canonical(name)
        best_match = None
        for zone in cls.objects.enabled().all():
            if name.endswith(zone.name):
                if not best_match or len(best_match.name) < len(zone.name):
                    best_match = zone
        return best_match

    @classmethod
    def match_ip(cls, ip:IPAddress) -> "[Zone]":
        """
        For a given IPAddress figure out the correct zones based on
        IPAddress, Interface, Device ir FHRPGroup tags or Device role.
        """
        def filter_mgmt_only(zones, ip):
            """ Checks if IP is assigned to interface.mgmt_only=True and finds matching zones """
            if not zones:
                # no results, just return
                return zones
            if not any(zones.values_list("match_interface_mgmt_only", flat=True)):
                # no zones are constrained to mgmt_only
                return zones
            if ip.interface.filter(mgmt_only=True):
                # IP is assigned to mgmt_only interface, return matching zones
                return zones.filter(match_interface_mgmt_only=True)
            else:
                # or just return zones
                return zones

        # tag on IPAddress
        zones = cls.objects.enabled().filter(match_ipaddress_tags__in=ip.tags.all())
        zones = filter_mgmt_only(zones, ip)
        if zones:
            return zones
        if isinstance(ip.assigned_object, Interface) or \
            isinstance(ip.assigned_object, VMInterface):
            # tag on Interface or VMInterface
            zones = cls.objects.enabled().filter(match_interface_tags__in=ip.assigned_object.tags.all())
            zones = filter_mgmt_only(zones, ip)
            if zones:
                return zones
            # tag on Device or VirtualMachine
            host = get_ip_host(ip)
            zones = cls.objects.enabled().filter(match_device_tags__in=host.tags.all())
            zones = filter_mgmt_only(zones, ip)
            if zones:
                return zones
        if isinstance(ip.assigned_object, FHRPGroup):
            zones = cls.objects.enabled().filter(match_fhrpgroup_tags__in=ip.assigned_object.tags.all())
            zones = filter_mgmt_only(zones, ip)
            if zones:
                return zones
        # role or device_role
        host = get_ip_host(ip)
        role = None
        # try: Device.device_role, VirtualMachine.role
        for role_name in ("device_role", "role"): 
            try:
                role = getattr(host, role_name)
            except AttributeError:
                continue
        if role:
            zones = cls.objects.enabled().filter(match_device_roles__in=[role])
            zones = filter_mgmt_only(zones, ip)
            if zones:
                return zones
        # default zone
        zones = cls.objects.enabled().filter(is_default=True)
        zones = filter_mgmt_only(zones, ip)
        if zones:
            return zones
        return cls.objects.empty()

    clone_fields = (
        "name", "description", "api_servers", "default_ttl",
        "match_ipaddress_tags", "match_interface_tags", "match_device_tags",
        "match_fhrpgroup_tags", "match_device_roles", "match_interface_mgmt_only",
        "naming_ip_method", "naming_device_method", "naming_fgrpgroup_method",
        "tags",
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="unique_is_default",
                violation_error_message="Only one zone can be set as default",
            )
        ]

    def get_absolute_url(self):
        return reverse("plugins:netbox_powerdns_sync:zone", args=[self.pk])

    def __str__(self):
        return self.name
