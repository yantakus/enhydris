from datetime import datetime
from unittest import skipIf
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test.utils import override_settings
from rest_framework.test import APITestCase

import iso8601
import pandas as pd
from model_mommy import mommy

from enhydris import models


class Tsdata404TestCase(APITestCase):
    def test_get_nonexistent_timeseries(self):
        response = self.client.get("/api/tsdata/1234/")
        self.assertEqual(response.status_code, 404)

    def test_post_nonexistent_timeseries(self):
        response = self.client.post("/api/tsdata/1234/")
        self.assertEqual(response.status_code, 404)


class TsdataGetTestCase(APITestCase):
    @patch(
        "enhydris.models.Timeseries.get_data",
        return_value=pd.DataFrame(
            index=[datetime(2017, 11, 23, 17, 23), datetime(2018, 11, 25, 1, 0)],
            data={"value": [1.0, 2.0], "flags": ["", ""]},
            columns=["value", "flags"],
        ),
    )
    def setUp(self, m):
        timeseries = mommy.make(models.Timeseries)
        self.response = self.client.get("/api/tsdata/{}/".format(timeseries.id))

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_content_type(self):
        self.assertEqual(self.response["Content-Type"], "text/plain")

    def test_response_content(self):
        self.assertEqual(
            self.response.content.decode(),
            "2017-11-23 17:23,1.000000,\r\n" "2018-11-25 01:00,2.000000,\r\n",
        )


class TsdataPostTestCase(APITestCase):
    @patch("enhydris.models.Timeseries.append_data")
    def setUp(self, m):
        self.mock_append_data = m
        user = mommy.make(User, username="admin", is_superuser=True)
        station = mommy.make(models.Station)
        timeseries = mommy.make(models.Timeseries, gentity=station)
        self.client.force_authenticate(user=user)
        self.response = self.client.post(
            "/api/tsdata/{}/".format(timeseries.id),
            data={
                "timeseries_records": (
                    "2017-11-23 17:23,1.000000,\r\n" "2018-11-25 01:00,2.000000,\r\n",
                )
            },
        )

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 204)

    def test_called_append_data(self):
        self.assertEqual(self.mock_append_data.call_count, 1)

    def test_called_append_data_with_correct_data(self):
        self.assertEqual(
            self.mock_append_data.call_args[0][0].getvalue(),
            "2017-11-23 17:23,1.000000,\r\n" "2018-11-25 01:00,2.000000,\r\n",
        )


class TsdataPostAuthorizationTestCase(APITestCase):
    def setUp(self):
        self.user1 = mommy.make(User, is_active=True, is_superuser=False)
        self.user2 = mommy.make(User, is_active=True, is_superuser=False)
        station = mommy.make(models.Station, creator=self.user1)
        self.timeseries = mommy.make(models.Timeseries, gentity=station)

    def _post_tsdata(self):
        return self.client.post(
            "/api/tsdata/{}/".format(self.timeseries.id),
            data={
                "timeseries_records": (
                    "2017-11-23 17:23,1.000000,\r\n" "2018-11-25 01:00,2.000000,\r\n",
                )
            },
        )

    @patch("enhydris.models.Timeseries.append_data")
    def test_unauthenticated_user_is_denied_permission_to_post_tsdata(self, m):
        self.assertEqual(self._post_tsdata().status_code, 401)

    @patch("enhydris.models.Timeseries.append_data")
    def test_unauthorized_user_is_denied_permission_to_post_tsdata(self, m):
        self.client.force_authenticate(user=self.user2)
        self.assertEqual(self._post_tsdata().status_code, 403)

    @patch("enhydris.models.Timeseries.append_data")
    def test_authorized_user_can_posttsdata(self, m):
        self.client.force_authenticate(user=self.user1)
        self.assertEqual(self._post_tsdata().status_code, 204)


class TsdataPostGarbageTestCase(APITestCase):
    @patch("enhydris.models.Timeseries.append_data", side_effect=iso8601.ParseError)
    def setUp(self, m):
        self.mock_append_data = m
        user = mommy.make(User, username="admin", is_superuser=True)
        station = mommy.make(models.Station)
        timeseries = mommy.make(models.Timeseries, gentity=station)
        self.client.force_authenticate(user=user)
        self.response = self.client.post(
            "/api/tsdata/{}/".format(timeseries.id),
            data={
                "timeseries_records": (
                    # The actual content doesn't matter, since the mock will raise
                    # an error.
                    "2017-11-23 17:23,1.000000,\r\n"
                    "2018-aa-25 01:00,2.000000,\r\n",
                )
            },
        )

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 400)


class TimeseriesPostTestCase(APITestCase):
    def setUp(self):
        self.user1 = mommy.make(User, is_active=True, is_superuser=False)
        self.user2 = mommy.make(User, is_active=True, is_superuser=False)
        self.variable = mommy.make(models.Variable)
        self.time_zone = mommy.make(models.TimeZone)
        self.unit_of_measurement = mommy.make(models.UnitOfMeasurement)
        self.station = mommy.make(models.Station, creator=self.user1)

    def _create_timeseries(self):
        return self.client.post(
            "/api/Timeseries/",
            data={
                "name": "Great time series",
                "gentity": self.station.id,
                "variable": self.variable.id,
                "time_zone": self.time_zone.id,
                "unit_of_measurement": self.unit_of_measurement.id,
            },
        )

    def test_unauthenticated_user_is_denied_permission_to_create_timeseries(self):
        self.assertEqual(self._create_timeseries().status_code, 401)

    def test_unauthorized_user_is_denied_permission_to_create_timeseries(self):
        self.client.force_authenticate(user=self.user2)
        self.assertEqual(self._create_timeseries().status_code, 403)

    def test_authorized_user_can_create_timeseries(self):
        self.client.force_authenticate(user=self.user1)
        self.assertEqual(self._create_timeseries().status_code, 201)


class TimeseriesDeleteTestCase(APITestCase):
    def setUp(self):
        self.user1 = mommy.make(User, is_active=True, is_superuser=False)
        self.user2 = mommy.make(User, is_active=True, is_superuser=False)
        station = mommy.make(models.Station, creator=self.user1)
        self.timeseries = mommy.make(models.Timeseries, gentity=station)

    def test_unauthenticated_user_is_denied_permission_to_delete_timeseries(self):
        response = self.client.delete("/api/Timeseries/{}/".format(self.timeseries.id))
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_user_is_denied_permission_to_delete_timeseries(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete("/api/Timeseries/{}/".format(self.timeseries.id))
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_can_delete_timeseries(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete("/api/Timeseries/{}/".format(self.timeseries.id))
        self.assertEqual(response.status_code, 204)


class StationListTestCase(APITestCase):
    def setUp(self):
        self.station = mommy.make(models.Station, name="Hobbiton")
        self.response = self.client.get("/api/Station/")

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_returned_items(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_name(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Hobbiton")


class StationCreateTestCase(APITestCase):
    def setUp(self):
        self.user = mommy.make(User, is_active=True, is_superuser=False)
        self.variable = mommy.make(models.Variable)
        self.time_zone = mommy.make(models.TimeZone)
        self.unit_of_measurement = mommy.make(models.UnitOfMeasurement)
        self.bilbo = mommy.make(models.Person, last_name="Baggins", first_name="Bilbo")
        self.meteorological = mommy.make(models.StationType, descr="Meteorological")

    def _create_station(self):
        return self.client.post(
            "/api/Station/",
            data={
                "name": "Hobbiton",
                "copyright_years": "2018",
                "copyright_holder": "Bilbo Baggins",
                "owner": self.bilbo.id,
                "stype": [self.meteorological.id],
            },
        )

    def test_unauthenticated_user_is_denied_permission_to_create_station(self):
        response = self._create_station()
        self.assertEqual(response.status_code, 401)

    @override_settings(ENHYDRIS_USERS_CAN_ADD_CONTENT=False)
    def test_unauthorized_user_is_denied_permission_to_create_station(self):
        self.client.force_authenticate(user=self.user)
        response = self._create_station()
        self.assertEqual(response.status_code, 403)

    @override_settings(ENHYDRIS_USERS_CAN_ADD_CONTENT=False)
    def test_authorized_user_can_create_station(self):
        permission = Permission.objects.get(codename="add_station")
        self.user.user_permissions.add(permission)
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self._create_station()
        self.assertEqual(response.status_code, 201)

    @override_settings(ENHYDRIS_USERS_CAN_ADD_CONTENT=True)
    def test_any_user_can_create_station_when_system_is_open(self):
        self.client.force_authenticate(user=self.user)
        response = self._create_station()
        self.assertEqual(response.status_code, 201)


class StationUpdateAndDeleteTestCase(APITestCase):
    def setUp(self):
        self.user1 = mommy.make(User, is_active=True, is_superuser=False)
        self.user2 = mommy.make(User, is_active=True, is_superuser=False)
        self.variable = mommy.make(models.Variable)
        self.time_zone = mommy.make(models.TimeZone)
        self.unit_of_measurement = mommy.make(models.UnitOfMeasurement)
        self.station = mommy.make(models.Station, creator=self.user1)
        self.bilbo = mommy.make(models.Person, last_name="Baggins", first_name="Bilbo")
        self.meteorological = mommy.make(models.StationType, descr="Meteorological")

    def _put_station(self):
        return self.client.put(
            "/api/Station/{}/".format(self.station.id),
            data={
                "name": "Hobbiton",
                "copyright_years": "2018",
                "copyright_holder": "Bilbo Baggins",
                "owner": self.bilbo.id,
                "stype": [self.meteorological.id],
            },
        )

    def _patch_station(self):
        return self.client.patch(
            "/api/Station/{}/".format(self.station.id), data={"name": "Hobbiton"}
        )

    def _delete_station(self):
        return self.client.delete("/api/Station/{}/".format(self.station.id))

    def test_unauthenticated_user_is_denied_permission_to_put_station(self):
        response = self._put_station()
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_user_is_denied_permission_to_put_station(self):
        self.client.force_authenticate(user=self.user2)
        response = self._put_station()
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_can_put_station(self):
        self.client.force_authenticate(user=self.user1)
        response = self._put_station()
        self.assertEqual(response.status_code, 200, response.content)

    def test_unauthenticated_user_is_denied_permission_to_patch_station(self):
        response = self._patch_station()
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_user_is_denied_permission_to_patch_station(self):
        self.client.force_authenticate(user=self.user2)
        response = self._patch_station()
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_can_patch_station(self):
        self.client.force_authenticate(user=self.user1)
        response = self._patch_station()
        self.assertEqual(response.status_code, 200, response.content)

    def test_unauthenticated_user_is_denied_permission_to_delete_station(self):
        response = self._delete_station()
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_user_is_denied_permission_to_delete_station(self):
        self.client.force_authenticate(user=self.user2)
        response = self._delete_station()
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_can_delete_station(self):
        self.client.force_authenticate(user=self.user1)
        response = self._delete_station()
        self.assertEqual(response.status_code, 204, response.content)


class StationSearchByOwnerTestCase(APITestCase):
    def setUp(self):
        owner1 = mommy.make(models.Organization, name="The Assassination Bureau, Ltd")
        owner2 = mommy.make(models.Organization, name="United Federation of Planets")
        mommy.make(models.Station, owner=owner1, name="Hobbiton")
        mommy.make(models.Station, owner=owner2, name="Rivendell")
        self.response = self.client.get("/api/Station/?", {"q": "owner:assassination"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Hobbiton")


class StationSearchByTypeTestCase(APITestCase):
    def setUp(self):
        mommy.make(models.Station, stype__descr=["Hydrometric"], name="Hobbiton")
        mommy.make(models.Station, stype__descr=["Elfometric"], name="Rivendell")
        self.response = self.client.get("/api/Station/?", {"q": "type:elf"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Rivendell")


class StationSearchByWaterDivisionTestCase(APITestCase):
    def setUp(self):
        mommy.make(models.Station, water_division__name="Mordor", name="Gorgoroth")
        mommy.make(models.Station, water_division__name="Gondor", name="Pelargir")
        self.response = self.client.get("/api/Station/?", {"q": "water_division:ordor"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Gorgoroth")


class StationSearchByWaterBasinTestCase(APITestCase):
    def setUp(self):
        mommy.make(models.Station, water_basin__name="Baranduin", name="Hobbiton")
        mommy.make(models.Station, water_basin__name="Lhûn", name="Mithlond")
        self.response = self.client.get("/api/Station/?", {"q": "water_basin:andu"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Hobbiton")


class StationSearchByVariableTestCase(APITestCase):
    def setUp(self):
        station1 = mommy.make(models.Station, name="Hobbiton")
        station2 = mommy.make(models.Station, name="Mithlond")
        mommy.make(models.Timeseries, gentity=station1, variable__descr="Rain")
        mommy.make(models.Timeseries, gentity=station2, variable__descr="Temperature")
        self.response = self.client.get("/api/Station/?", {"q": "variable:rain"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Hobbiton")


class StationSearchByTsOnlyTestCase(APITestCase):
    def setUp(self):
        station1 = mommy.make(models.Station, name="Hobbiton")
        mommy.make(models.Timeseries, gentity=station1)
        mommy.make(models.Station, name="Mithlond")
        self.response = self.client.get("/api/Station/?", {"q": "ts_only:"})

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Hobbiton")


def check_if_connected_to_old_sqlite():
    """Return True if connected to sqlite<3.8.3

    Used to skip a test, notably on Travis, which currently runs an old sqlite
    version.

    The correct way would have been to remove the functionality, not just skip
    the test, because the functionality is still there and will cause an
    internal server error, but this would be too much work given that we use
    SQLite only for development.
    """
    try:
        from django.contrib.gis.db.backends.spatialite import base
        import sqlite3
    except ImportError:
        return False
    if not isinstance(connections[DEFAULT_DB_ALIAS], base.DatabaseWrapper):
        return False
    major, minor, micro = [int(x) for x in sqlite3.sqlite_version.split(".")[:3]]
    return (
        (major < 3)
        or (major == 3 and minor < 8)
        or (major == 3 and minor == 8 and micro < 3)
    )


class PoliticalDivisionTestCaseBase(APITestCase):
    def setUp(self):
        mommy.make(
            models.Station,
            name="Komboti",
            political_division__name="Arta",
            political_division__parent__name="Epirus",
            political_division__parent__parent__name="Greece",
        )
        mommy.make(
            models.Station,
            name="Tharbad",
            political_division__name="Cardolan",
            political_division__parent__name="Eriador",
            political_division__parent__parent__name="Middle Earth",
        )


@skipIf(check_if_connected_to_old_sqlite(), "Use sqlite>=3.8.3")
class StationSearchBy2ndLevelPoliticalDivisionTestCase(PoliticalDivisionTestCaseBase):
    def setUp(self):
        super().setUp()
        self.response = self.client.get(
            "/api/Station/?",
            {"q": "political_division:Epirus"},
        )

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Komboti")


@skipIf(check_if_connected_to_old_sqlite(), "Use sqlite>=3.8.3")
class StationSearchBy3rdLevelPoliticalDivisionTestCase(PoliticalDivisionTestCaseBase):
    def setUp(self):
        super().setUp()
        self.response = self.client.get(
            "/api/Station/?",
            {"q": "political_division:earth"},
        )

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Tharbad")


class StationSearchInTimeseriesRemarksTestCase(APITestCase):
    def setUp(self):
        station1 = mommy.make(models.Station, name="Hobbiton")
        mommy.make(
            models.Timeseries,
            gentity=station1,
            remarks="This is an extremely important time series",
        )
        station2 = mommy.make(models.Station, name="Mithlond")
        mommy.make(
            models.Timeseries,
            gentity=station2,
            remarks="This time series is really important",
        )
        self.response = self.client.get(
            "/api/Station/?",
            {"q": "really important time series"}
        )

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_number_of_results(self):
        self.assertEqual(len(self.response.json()["results"]), 1)

    def test_results(self):
        self.assertEqual(self.response.json()["results"][0]["name"], "Mithlond")


class WaterDivisionTestCase(APITestCase):
    def setUp(self):
        self.water_division = mommy.make(models.WaterDivision)

    def test_get_water_division(self):
        r = self.client.get("/api/WaterDivision/{}/".format(self.water_division.id))
        self.assertEqual(r.status_code, 200)


class GentityAltCodeTypeTestCase(APITestCase):
    def setUp(self):
        self.gentity_alt_code_type = mommy.make(models.GentityAltCodeType)

    def test_get_gentity_alt_code_type(self):
        r = self.client.get(
            "/api/GentityAltCodeType/{}/".format(self.gentity_alt_code_type.id)
        )
        self.assertEqual(r.status_code, 200)


class OrganizationTestCase(APITestCase):
    def setUp(self):
        self.organization = mommy.make(models.Organization)

    def test_get_organization(self):
        r = self.client.get("/api/Organization/{}/".format(self.organization.id))
        self.assertEqual(r.status_code, 200)


class PersonTestCase(APITestCase):
    def setUp(self):
        self.person = mommy.make(models.Person)

    def test_get_person(self):
        r = self.client.get("/api/Person/{}/".format(self.person.id))
        self.assertEqual(r.status_code, 200)


class StationTypeTestCase(APITestCase):
    def setUp(self):
        self.station_type = mommy.make(models.StationType)

    def test_get_station_type(self):
        r = self.client.get("/api/StationType/{}/".format(self.station_type.id))
        self.assertEqual(r.status_code, 200)


class TimeZoneTestCase(APITestCase):
    def setUp(self):
        self.time_zone = mommy.make(models.TimeZone)

    def test_get_time_zone(self):
        r = self.client.get("/api/TimeZone/{}/".format(self.time_zone.id))
        self.assertEqual(r.status_code, 200)


class PoliticalDivisionTestCase(APITestCase):
    def setUp(self):
        self.political_division = mommy.make(models.PoliticalDivision)

    def test_get_political_division(self):
        r = self.client.get(
            "/api/PoliticalDivision/{}/".format(self.political_division.id)
        )
        self.assertEqual(r.status_code, 200)


class IntervalTypeTestCase(APITestCase):
    def setUp(self):
        self.interval_type = mommy.make(models.IntervalType)

    def test_get_interval_type(self):
        r = self.client.get("/api/IntervalType/{}/".format(self.interval_type.id))
        self.assertEqual(r.status_code, 200)


class FileTypeTestCase(APITestCase):
    def setUp(self):
        self.file_type = mommy.make(models.FileType)

    def test_get_file_type(self):
        r = self.client.get("/api/FileType/{}/".format(self.file_type.id))
        self.assertEqual(r.status_code, 200)


class EventTypeTestCase(APITestCase):
    def setUp(self):
        self.event_type = mommy.make(models.EventType)

    def test_get_event_type(self):
        r = self.client.get("/api/EventType/{}/".format(self.event_type.id))
        self.assertEqual(r.status_code, 200)


class InstrumentTypeTestCase(APITestCase):
    def setUp(self):
        self.instrument_type = mommy.make(models.InstrumentType)

    def test_get_instrument_type(self):
        r = self.client.get("/api/InstrumentType/{}/".format(self.instrument_type.id))
        self.assertEqual(r.status_code, 200)


class WaterBasinTestCase(APITestCase):
    def setUp(self):
        self.water_basin = mommy.make(models.WaterBasin)

    def test_get_water_basin(self):
        r = self.client.get("/api/WaterBasin/{}/".format(self.water_basin.id))
        self.assertEqual(r.status_code, 200)


class TimeStepTestCase(APITestCase):
    def setUp(self):
        self.time_step = mommy.make(models.TimeStep, length_minutes=10, length_months=0)

    def test_get_time_step(self):
        r = self.client.get("/api/TimeStep/{}/".format(self.time_step.id))
        self.assertEqual(r.status_code, 200)


class VariableTestCase(APITestCase):
    def setUp(self):
        self.variable = mommy.make(models.Variable)

    def test_get_variable(self):
        r = self.client.get("/api/Variable/{}/".format(self.variable.id))
        self.assertEqual(r.status_code, 200)


class UnitOfMeasurementTestCase(APITestCase):
    def setUp(self):
        self.unit_of_measurement = mommy.make(models.UnitOfMeasurement)

    def test_get_unit_of_measurement(self):
        r = self.client.get(
            "/api/UnitOfMeasurement/{}/".format(self.unit_of_measurement.id)
        )
        self.assertEqual(r.status_code, 200)
