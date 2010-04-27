import string
from django.shortcuts import get_object_or_404
from piston.handler import BaseHandler
from piston.utils import rc
from enhydris.hcore.models import *

class StationHandler(BaseHandler):
    model = Station
    fields = ('id', 'name', 'srid', 'abscissa', 'ordinate', 'altitude',
                'asrid','is_active',
                ('water_basin',('name',)),
                ('water_division',('name',)),
                ('political_division',('name',)),
                ('type',('descr',)),
                ('owner',('name_any',)))

class StationListHandler(BaseHandler):
    allowed_methods = ('POST')
    model = Station
    fields = ('id', 'name', 'srid', 'abscissa', 'ordinate', 'altitude',
                'asrid','is_active',
                ('water_basin',('name',)),
                ('water_division',('name',)),
                ('political_division',('name',)),
                ('type',('descr',)),
                ('owner',('name_any',)))

    def create(self, request, *args, **kwargs):
        """
        Return a set of station objects.

        In fact there is no creation of object in this function. This function
        just reads a set of station ids and returns the corresponding station
        objects.
        """
        response = []
        if not request.POST.has_key('station_list'):
            return rc.BAD_REQUEST
        ids = string.split(request.POST['station_list'],sep=",")
        for station_id in ids:
            if station_id:
                try:
                    station = Station.objects.get(id=station_id)
                    response.append(station)
                except Station.DoesNotExist:
                    pass

        return response

# Timeseries handler for ts data
class TSDATA_Handler(BaseHandler):
    """
    This handler is responsible for taking a timeseries id and returning the
    actual timeseries data to the client.
    """
    def read(self, request, ts_id, *args, **kwargs):
        try:
            timeseries = Timeseries.objects.get(pk=int(ts_id))
        except:
            return rc.NOT_FOUND
        return timeseries

class GFDATA_Handler(BaseHandler):
    """
    This handler serves the GentityFile contents using piston API.
    """
    def read(self, request, gf_id, *args, **kwargs):
        try:
            gfile = GentityFile.objects.get(pk=int(gf_id))
        except:
            return rc.NOT_FOUND

        return gfile

# Regular handlers for the rest of the models
class Lookup_Handler(BaseHandler):
    """
    API handler for hcore model Lookup.
    """
    model = Lookup
    exclude = ()

class Lentity_Handler(BaseHandler):
    """
    API handler for hcore model Lentity.
    """
    model = Lentity
    exclude = ()

class Person_Handler(BaseHandler):
    """
    API handler for hcore model Person.
    """
    model = Person
    exclude = ()

class Organization_Handler(BaseHandler):
    """
    API handler for hcore model Organization.
    """
    model = Organization
    exclude = ()

class Gentity_Handler(BaseHandler):
    """
    API handler for hcore model Gentity.
    """
    model = Gentity
    exclude = ()

class Gpoint_Handler(BaseHandler):
    """
    API handler for hcore model Gpoint.
    """
    model = Gpoint
    exclude = ()

class Gline_Handler(BaseHandler):
    """
    API handler for hcore model Gline.
    """
    model = Gline
    exclude = ()

class Garea_Handler(BaseHandler):
    """
    API handler for hcore model Garea.
    """
    model = Garea
    exclude = ()

class PoliticalDivisionManager_Handler(BaseHandler):
    """
    API handler for hcore model PoliticalDivisionManager.
    """
    model = PoliticalDivisionManager
    exclude = ()

class PoliticalDivision_Handler(BaseHandler):
    """
    API handler for hcore model PoliticalDivision.
    """
    model = PoliticalDivision
    exclude = ()

class WaterDivision_Handler(BaseHandler):
    """
    API handler for hcore model WaterDivision.
    """
    model = WaterDivision
    exclude = ()

class WaterBasin_Handler(BaseHandler):
    """
    API handler for hcore model WaterBasin.
    """
    model = WaterBasin
    exclude = ()

class GentityAltCodeType_Handler(BaseHandler):
    """
    API handler for hcore model GentityAltCodeType.
    """
    model = GentityAltCodeType
    exclude = ()

class GentityAltCode_Handler(BaseHandler):
    """
    API handler for hcore model GentityAltCode.
    """
    model = GentityAltCode
    exclude = ()

class FileType_Handler(BaseHandler):
    """
    API handler for hcore model FileType.
    """
    model = FileType
    exclude = ()

class GentityFile_Handler(BaseHandler):
    """
    API handler for hcore model GentityFile.
    """
    model = GentityFile
    exclude = ()

class EventType_Handler(BaseHandler):
    """
    API handler for hcore model EventType.
    """
    model = EventType
    exclude = ()

class GentityEvent_Handler(BaseHandler):
    """
    API handler for hcore model GentityEvent.
    """
    model = GentityEvent
    exclude = ()

class StationType_Handler(BaseHandler):
    """
    API handler for hcore model StationType.
    """
    model = StationType
    exclude = ()

class StationManager_Handler(BaseHandler):
    """
    API handler for hcore model StationManager.
    """
    model = StationManager
    exclude = ()

class Station_Handler(BaseHandler):
    """
    API handler for hcore model Station.
    """
    model = Station
    exclude = ('creator',)

class Overseer_Handler(BaseHandler):
    """
    API handler for hcore model Overseer.
    """
    model = Overseer
    exclude = ()

class InstrumentType_Handler(BaseHandler):
    """
    API handler for hcore model InstrumentType.
    """
    model = InstrumentType
    exclude = ()

class Instrument_Handler(BaseHandler):
    """
    API handler for hcore model Instrument.
    """
    model = Instrument
    exclude = ()

class Variable_Handler(BaseHandler):
    """
    API handler for hcore model Variable.
    """
    model = Variable
    exclude = ()

class UnitOfMeasurement_Handler(BaseHandler):
    """
    API handler for hcore model UnitOfMeasurement.
    """
    model = UnitOfMeasurement
    exclude = ()

class TimeZone_Handler(BaseHandler):
    """
    API handler for hcore model TimeZone.
    """
    model = TimeZone
    exclude = ()

class TimeStep_Handler(BaseHandler):
    """
    API handler for hcore model TimeStep.
    """
    model = TimeStep
    exclude = ()

class Timeseries_Handler(BaseHandler):
    """
    API handler for hcore model Timeseries.
    """
    model = Timeseries
    exclude = ()
