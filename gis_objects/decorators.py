from django.db.models import Count
from enhydris.gis_objects.models import *
from enhydris.hcore.models import Timeseries


extra_field = { 'GISBorehole'       : 'group', 
                'GISPump'           : 'pump_active', 
                'GISRefinery'       : 'capacity',
                'GISSpring'         : 'dstype__descr', 
                'GISAqueductNode'   : 'group__descr',
                'GISAqueductLine'   : 'group__descr',
                'GISReservoir'      : 'area',
              }

def sort_by(f):
    def _dec(request, queryset, *args, **kwargs):
        nkwargs = kwargs
        if 'sort' in nkwargs:
            column = nkwargs['sort']
        elif request.GET.__contains__('sort'):
            column = request.GET['sort']
        else:
            column = 'name'
        direction = None
        if request.GET.__contains__('dir'):
            direction = request.GET['dir']
        listmodels = models_lst
        if request.GET.__contains__('gtype'):
            gtype = request.GET['gtype']
            if gtype.isdigit(): gtype = int(gtype)-1
            if gtype in range(7):
                listmodels = (models_lst[gtype],)
        if column in ('id', 'gtype'):
            orderargs = (column,)
        elif column == 'extra_info':
            orderargs = (str.lower(x)+'__'+extra_field[x] \
                                                  for x in listmodels)
        else:
            orderargs = (str.lower(x)+'__'+column for x in listmodels)
        if direction and direction=='asc':
            orderargs = ('-'+x for x in orderargs)
        queryset = queryset.order_by(*orderargs)
        return f(request, queryset, *args, **nkwargs)
    return _dec

def filter_by(f):
    def _dec(request, queryset, *args, **kwargs):
        nkargs = kwargs
        gtype = None
        if request.GET.__contains__('gtype'):
            gtype = request.GET['gtype']
        if gtype:
            queryset = queryset.filter(gtype=gtype)
        has_timeseries = False
        if request.GET.__contains__('timeseries'):
            has_timeseries = True if\
               (request.GET['timeseries']) in ('True', 'true', 
                                               'TRUE') else False
        if has_timeseries:
# Warning! I think that this radomly works, because not every
# GISEntity object has link from gisbhorele. But it works right
# now, maybe from django mechanism of queries, making the query
# to the top model. Should be Improved and tested.
# Stefanos, 2011-10-20
            queryset = queryset.filter(gisborehole__id__in=\
                      Timeseries.objects.all().values('gentity').query)
        return f(request, queryset, *args, **nkargs)
    return _dec
