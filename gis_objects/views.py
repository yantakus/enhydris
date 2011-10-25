from django.contrib.gis.shortcuts import render_to_kml
from django.contrib.gis.geos import Polygon
from django.http import Http404
from django.views.generic import list_detail
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models import Q
from enhydris.hcore.models import Timeseries
from enhydris.hcore.views import clean_kml_request
from enhydris.gis_objects.models import *
from enhydris.gis_objects.decorators import *

models = {'boreholes'       : [GISBorehole,_('Borehole')],
          'pumps'           : [GISPump,_('Pump')],
          'refineries'      : [GISRefinery,_('Refinery')],
          'springs'         : [GISSpring,_('Spring')],
          'aqueduct_nodes'  : [GISAqueductNode,_('Aqueduct node')],
          'aqueduct_lines'  : [GISAqueductLine,_('Aqueduct segment')],
          'reservoirs'      : [GISReservoir,_('Reservoir')],
          }

geom_type={ 'boreholes'         : 'point',
            'pumps'             : 'point',
            'refineries'        : 'point',
            'springs'           : 'point',
            'aqueduct_nodes'    : 'point',
            'aqueduct_lines'    : 'linestring',
            'reservoirs'        : 'mpoly',
          }

models_parent_id={ 'boreholes'  : 'gisboreholespring_ptr_id',
            'pumps'             : 'gpoint_ptr_id',
            'refineries'        : 'gpoint_ptr_id',
            'springs'           : 'gisboreholespring_ptr_id',
            'aqueduct_nodes'    : 'gpoint_ptr_id',
            'aqueduct_lines'    : 'gline_ptr_id',
            'reservoirs'        : 'garea_ptr_id',
          }

templates = {   'boreholes'     : 'borehole_detail.html',
                'pumps'         : 'pump_detail.html',
                'refineries'    : 'refinery_detail.html',
                'springs'       : 'spring_detail.html',
                'aqueduct_nodes': 'aqueduct_node_detail.html',
                'aqueduct_lines': 'aqueduct_segment_detail.html',
                'reservoirs'    : 'reservoir_detail.html',
            }

standard_search_fields = ('name', 'name_alt', 'short_name', 
                          'short_name_alt', 'gentity_ptr__remarks', 'remarks_alt',
                          'water_basin__name',
                          'water_basin__name_alt',
                          'water_division__name',
                          'water_division__name_alt',
                          'political_division__name',
                          'political_division__name_alt',)

models_extra_search_fields = {'gisborehole' : ('group',),
                              'gispump'     : ('pump_type__descr',
                                               'pump_type__descr_alt'),
                              'gisreservoir': (),
                              'gisrefinery' : (),
                              'gisspring'   : ('dstype__descr',
                                               'dstype__descr_alt'),
                              'gisaqueductnode': ('group__descr',
                                                  'group__descr_alt',
                                                  'type_name',
                                                 'repers','repers_en'),
                              'gisaqueductline': ('group__descr',
                                                  'group__descr_alt',
                                                  'remarks',
                                                  'type_name',
                                                 'repers', 
                                                 'repers_en'),}
                                                
def get_search_query(search_terms):
    query = Q()
    for term in search_terms:
        for model in models_extra_search_fields:
            for field in standard_search_fields +\
                         models_extra_search_fields[model]:
                akwarg={}
                akwarg['%s__%s__icontains'%(model, field,)]=term
                query |= Q(**akwarg)
    return query

def kml(request, layer):
    try:
        bbox=request.GET.get('BBOX', request.GET.get('bbox', None))
        other_id=request.GET.get('OTHER_ID', request.GET.get('other_id', None))
    except Exception, e:
        raise Http404
    if bbox:
        try:
            minx, miny, maxx, maxy=[float(i) for i in bbox.split(',')]
            geom=Polygon(((minx,miny),(minx,maxy),(maxx,maxy),(maxx,miny),(minx,miny)),srid=4326)
        except Exception, e:
            raise Http404
    try:
        getparams = clean_kml_request(request.GET.items())
        queryres = models[layer][0].objects.all()
        if getparams.has_key('check') and getparams['check']=='search':
            query_string = request.GET.get('q', request.GET.get('Q', ""))
            search_terms = query_string.split()
            if search_terms:
                queryres = queryres.filter(get_search_query(search_terms)).distinct()
        else:
            if bbox:
                if geom_type[layer]=='point':
                    queryres = queryres.filter(point__contained=geom)
                elif geom_type[layer]=='linestring':
                    queryres = queryres.filter(linestring__contained=geom)
                elif geom_type[layer]=='mpoly':
                    pass
    #                queryres = queryres.filter(mpoly__bboverlaps=geom)
                else:
                    assert(False)
            if getparams.has_key('timeseries'):
                queryres = queryres.filter(gentity_ptr__in=\
                             Timeseries.objects.all().values("gentity").query)
    except Exception, e:
        raise Http404
    if getparams.has_key('other_id'):
        queryres = queryres.filter(id=getparams['other_id'])
    for arow in queryres:
        if getattr(arow, geom_type[layer]): 
            arow.kml = getattr(arow, geom_type[layer]).kml
    response = render_to_kml('gis_objects.kml', {'places': queryres})
    return response


def gis_objects_brief(request, *args, **kwargs):
    object_id = kwargs['object_id']
    found = False
    for model in models:
        if models[model][0].objects.filter(id=object_id).exists():
            kwargs["extra_context"] = {'type': models[model][1],}
            found = True
            amodel = model
            break
    if not found:
        raise Http404;
    kwargs['object_id'] = getattr(models[amodel][0].objects.get(\
                                  gisentity_ptr = kwargs['object_id']), 
                            models_parent_id[amodel])
    return list_detail.object_detail(request,
                                     queryset=models[amodel][0].objects.all(),
                                     template_object_name = "object",
                                     template_name = "gis_objects_brief.html",
                                     **kwargs)

def gis_objects_detail(request, *args, **kwargs):
    anonymous_can_download_data = False
    if hasattr(settings, 'TSDATA_AVAILABLE_FOR_ANONYMOUS_USERS') and\
            settings.TSDATA_AVAILABLE_FOR_ANONYMOUS_USERS:
        anonymous_can_download_data = True
    object_id = kwargs['object_id']
    kwargs['extra_context']={'use_open_layers': True,
        "anonymous_can_download_data": anonymous_can_download_data,}
    found = False
    for model in models:
        if models[model][0].objects.filter(id=object_id).exists():
            found = True
            amodel = model
            break
    if not found:
        raise Http404;
    kwargs['object_id'] = getattr(models[amodel][0].objects.get(\
                                  gisentity_ptr = kwargs['object_id']), 
                            models_parent_id[amodel])
    return list_detail.object_detail(request,
                                     queryset=models[amodel][0].objects.all(),
                                     template_object_name = "object",
                                     template_name = templates[amodel],
                                     **kwargs)
@sort_by
@filter_by
def gis_objects_list(request, queryset, *args, **kwargs):
    if request.GET.has_key("check") and request.GET["check"]=="search":
        # The case we got a simple search request
#        kwargs["extra_context"].update({"search":True})
        query_string = request.GET.get('q', "")
        search_terms = query_string.split()
        results = queryset
        if search_terms:
            results = results.filter(get_search_query(search_terms)).distinct()
            queryset = results
        else:
            results = []
#        kwargs["extra_context"].update({'query': query_string,
#                                        'terms': search_terms, })
    gtypes = GISEntityType.objects.all()
    kwargs["extra_context"] = { "use_open_layers": True,
                                "gtypes": gtypes}
    kwargs["template_name"] = "gis_objects_list.html"
    return list_detail.object_list(request, queryset, *args, **kwargs )
    
