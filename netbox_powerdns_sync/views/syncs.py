from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from core.models import Job
from utilities.htmx import is_htmx
from utilities.rqworker import get_workers_for_queue
from utilities.utils import normalize_querydict
from utilities.views import ContentTypePermissionRequiredMixin

from ..constants import JOB_NAME_DEVICE, JOB_NAME_INTERFACE, JOB_NAME_IP, JOB_NAME_SYNC
from ..jobs import PowerdnsTaskFullSync
from ..forms import ZoneScheduleForm
from ..models import Zone
from ..tables import SyncJobTable

__all__ = (
    "SyncJobsView",
    "SyncResultView",
    "SyncScheduleView",
)


class aaaSyncRunView(ContentTypePermissionRequiredMixin, View):

    def get_required_permission(self):
        return "extras.view_script"

    def get(self, request, pk):
        if not request.user.has_perm("extras.run_script"):
            return HttpResponseForbidden()

        zone = get_object_or_404(Zone.objects.restrict(request.user), pk=pk)
        if not zone.enabled:
            messages.error(request, f"Unable to sync disabled zone {zone}")
        elif not get_workers_for_queue("default"):
            messages.error(request, "Unable to run script: RQ worker process not running.")
        else:
            job = Job.enqueue(
                PowerdnsTaskFullSync.run_full_sync,
                instance=zone,
                name=JOB_NAME_SYNC,
                user=request.user,
            )
            return redirect("plugins:netbox_powerdns_sync:sync_result", job_pk=job.pk)

        return redirect(zone)


class SyncJobsView(ContentTypePermissionRequiredMixin, View):

    def get_required_permission(self):
        return "extras.view_script"

    def get(self, request):
        query = Q(app_label="netbox_powerdns_sync", model="zone")|Q(app_label="ipam", model="ipaddress")
        object_types = ContentType.objects.filter(query)
        jobs = Job.objects.filter(
            object_type__in=object_types,
            name__in=(JOB_NAME_DEVICE, JOB_NAME_INTERFACE, JOB_NAME_IP, JOB_NAME_SYNC),
        )
        jobs_table = SyncJobTable(
            data=jobs,
            orderable=False,
            user=request.user
        )
        jobs_table.configure(request)

        return render(request, "netbox_powerdns_sync/syncs.html", {
            "table": jobs_table,
            "tab": "jobs",
        })


class SyncResultView(ContentTypePermissionRequiredMixin, View):

    def get_required_permission(self):
        return "extras.view_script"

    def get(self, request, job_pk):
        #object_type = ContentType.objects.get_by_natural_key(app_label="extras", model="scriptmodule")
        #job = get_object_or_404(Job.objects.all(), pk=job_pk, object_type=object_type)
        job = get_object_or_404(Job.objects.all(), pk=job_pk)

        #module = job.object
        #script = module.scripts[job.name]()

        # If this is an HTMX request, return only the result HTML
        if is_htmx(request):
            response = render(request, "netbox_powerdns_sync/htmx/sync_result.html", {
                #"script": script,
                "job": job,
            })
            if job.completed or not job.started:
                response.status_code = 286
            return response

        return render(request, "netbox_powerdns_sync/sync_result.html", {
            #"script": script,
            "job": job,
        })


class SyncScheduleView(View):
    def get(self, request):
        scheduled_jobs = Job.objects.filter(status="scheduled", name=JOB_NAME_SYNC)
        jobs_table = SyncJobTable(
            data=scheduled_jobs,
            orderable=False,
            user=request.user
        )
        jobs_table.columns.show("scheduled")
        jobs_table.columns.show("interval")
        jobs_table.columns.show("object")
        jobs_table.configure(request)

        form = ZoneScheduleForm(initial=normalize_querydict(request.GET))

        return render(request, "netbox_powerdns_sync/sync_schedule.html", {
            "jobs_table": jobs_table,
            "form": form,
        })

    def post(self, request):
        form = ZoneScheduleForm(request.POST, request.FILES)
        
        if not get_workers_for_queue("default"):
            messages.error(request, "Unable to run script: RQ worker process not running.")
        elif form.is_valid():
            for zone in form.cleaned_data["zones"]:
                Job.enqueue(
                    PowerdnsTaskFullSync.run_full_sync,
                    instance=zone,
                    name=JOB_NAME_SYNC,
                    user=request.user,
                    schedule_at=form.cleaned_data.get("_schedule_at"),
                    interval=form.cleaned_data.get("_interval"),
                )
                messages.success(request, f"Scheduled sync job for zone {zone}")

        return redirect("plugins:netbox_powerdns_sync:sync_jobs")
