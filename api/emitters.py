import mimetypes
import os
import pthelma
from django.core import serializers
from django.core.servers.basehttp import FileWrapper
from django.db import connection as django_db_connection
from django.http import HttpResponse
from piston.emitters import Emitter
from enhydris.hcore.models import Timeseries, TimeStep

class CFEmitter(Emitter):
    """
    Custom Fixture emitter.

    Creates JSON fixtures of a model the same way the dumpdata management
    command does. The client, running code similar to loaddata, reads the JSON
    fixtures and updates the db.
    """
    def render(self, request):
        """
        Render function which serializes the actual data.
        """
        cb = request.GET.get('callback')
        seria = serializers.serialize('json', self.data, indent=1)

        # Callback
        if cb:
            return '%s(%s)' % (cb, seria)

        return seria


class TSEmitter(Emitter):
    """
    This emitter takes care of export all ts data from the db and then sending
    them back to the user as a file.
    """
    def construct(self):

        return None

    def render(self, request):
        timeseries = self.data
        # Determine time step and convert it to old format
        t = timeseries # nickname, because we use it much in next statement
        ts = pthelma.timeseries.Timeseries(
            id = int(t.id),
            time_step = pthelma.timeseries.TimeStep(
                length_minutes = t.time_step.length_minutes if t.time_step
                                            else 0,
                length_months = t.time_step.length_months if t.time_step
                                            else 0,
                nominal_offset = (t.nominal_offset_minutes,
                                         t.nominal_offset_months),
                actual_offset = (t.actual_offset_minutes,
                                         t.actual_offset_months)
            ),
            unit = t.unit_of_measurement.symbol,
            title = t.name,
            timezone = '%s (UTC+%02d%02d)' % (t.time_zone.code,
                t.time_zone.utc_offset / 60, t.time_zone.utc_offset % 60),
            variable = t.variable.descr,
            precision = t.precision,
            comment = '%s\n\n%s' % (t.gentity.name, t.remarks)
        )
        ts.read_from_db(django_db_connection)
        response = HttpResponse(mimetype=
                                'text/vnd.openmeteo.timeseries; charset=utf-8')
        response['Content-Disposition'] = "attachment; filename=%s.hts"%(t.id,)
        ts.write_file(response)
        return response

class GFEmitter(Emitter):
    """
    This emitter takes care of reading the GentityFile contents and then
    neding them back to the user as a file.
    """
    def construct(self):
        return None

    def render(self, request):
        gfile = self.data
        filename = gfile.content.file.name
        wrapper = FileWrapper(open(filename))
        download_name = gfile.content.name.split('/')[-1]
        content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(mimetype=content_type)
        response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = "attachment;filename=%s"%download_name

        for chunk in wrapper:
            response.write(chunk)

        return response
