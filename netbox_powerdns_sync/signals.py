import logging

from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_save

from core.models import Job
from dcim.models import Device, Interface
from extras.plugins import get_plugin_config
from ipam.models import IPAddress, FHRPGroup
from netbox.context import current_request
from virtualization.models import VirtualMachine, VMInterface

from .constants import JOB_NAME_DEVICE, JOB_NAME_INTERFACE, JOB_NAME_IP, PLUGIN_NAME
from .jobs import PowerdnsTaskIP
from .utils import find_objectchange_ip


logger = logging.getLogger("netbox.netbox_powerdns_sync.signals")

IPADDRESS_DNS_FIELDS = (
    "address",
    "dns_name",
    "assigned_object_id",
    "assigned_object_type",
)

INTERFACE_DNS_FIELDS = (
    "name",
)

DEVICE_DNS_FIELDS = (
    "name",
    "primary_ip4",
    "primary_ip6",
)


@receiver(post_save, sender=IPAddress)
def update_ipaddress_dns(instance, **kwargs):
    if not get_plugin_config(PLUGIN_NAME, "post_save_enabled"):
        return
    changed = True
    if hasattr(instance, "_prechange_snapshot"):
        prechange_snapshot = instance._prechange_snapshot
        postchange_snapshot = instance.serialize_object()
        # determine if important fields changed
        changed = False
        for field in IPADDRESS_DNS_FIELDS:
            if prechange_snapshot.get(field) != postchange_snapshot.get(field):
                changed = True
    if not changed:
        # nothing interesting changed, nothing to do
        return
    job_args = dict(
        func=PowerdnsTaskIP.run_update_ip,
        instance=instance,
        name=JOB_NAME_IP,
    )
    request = current_request.get()
    if request:
        job_args["user"] = request.user
    transaction.on_commit(lambda: Job.enqueue(**job_args))


@receiver(post_save, sender=Interface)
@receiver(post_save, sender=VMInterface)
@receiver(post_save, sender=FHRPGroup)
def update_interface_dns(instance: FHRPGroup, **kwargs):
    if not get_plugin_config(PLUGIN_NAME, "post_save_enabled"):
        return
    changed = True
    if hasattr(instance, "_prechange_snapshot"):
        prechange_snapshot = instance._prechange_snapshot
        postchange_snapshot = instance.serialize_object()
        # determine if relevant fields changed
        changed = False
        for field in INTERFACE_DNS_FIELDS:
            if prechange_snapshot.get(field) != postchange_snapshot.get(field):
                changed = True
    if not changed:
        # nothing interesting changed, nothing to do
        return
    # need to create job for IPv4 and IPv6
    job_args = dict(
        func=PowerdnsTaskIP.run_update_ip,
        name=JOB_NAME_INTERFACE,
    )
    request = current_request.get()
    if request:
        job_args["user"] = request.user
    for ip_address in instance.ip_addresses.all():
        job_args["instance"] = ip_address
        transaction.on_commit(lambda: Job.enqueue(**job_args))


@receiver(post_save, sender=Device)
@receiver(post_save, sender=VirtualMachine)
def update_device_dns(instance, **kwargs):
    if not get_plugin_config(PLUGIN_NAME, "post_save_enabled"):
        return
    changed = False
    if hasattr(instance, "_prechange_snapshot"):
        prechange_snapshot = instance._prechange_snapshot
        postchange_snapshot = instance.serialize_object()
        # determine if relevant fields changed
        changed = False
        for field in DEVICE_DNS_FIELDS:
            if prechange_snapshot.get(field) != postchange_snapshot.get(field):
                changed = True
    if not changed:
        # nothing interesting changed, nothing to do
        return
    request = current_request.get()
    # need to create job for IPv4 and IPv6
    if instance.primary_ip4:
        enqueue_task = True
        job_args = dict(
            func=PowerdnsTaskIP.run_update_ip,
            instance=instance.primary_ip4,
            name=JOB_NAME_DEVICE,
        )
        if request:
            job_args["user"] = request.user
            # check if IPAddress object was creted in same request
            q_created = find_objectchange_ip(instance.primary_ip4, request.id)
            enqueue_task = not q_created.exists()
        if enqueue_task:
            transaction.on_commit(lambda: Job.enqueue(**job_args))
    if instance.primary_ip6:
        enqueue_task = True
        job_args = dict(
            func=PowerdnsTaskIP.run_update_ip,
            instance=instance.primary_ip6,
            name=JOB_NAME_DEVICE,
        )
        if request:
            job_args["user"] = request.user
            # check if IPAddress object was creted in same request
            q_created = find_objectchange_ip(instance.primary_ip6, request.id)
            enqueue_task = not q_created.exists()
        if enqueue_task:
            transaction.on_commit(lambda: Job.enqueue(**job_args))
