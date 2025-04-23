from abc import ABCMeta, abstractmethod
from os import path
from typing import Any, Final, override
from uuid import uuid4

import pytest
from azure.storage.blob.aio import ContainerClient
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from meldingen_core.malware import BaseMalwareScanner
from meldingen_core.statemachine import MeldingStates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from meldingen.models import Attachment, Classification, Form, Melding, Question
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestMeldingCreate:
    ROUTE_NAME_CREATE: Final[str] = "melding:create"

    @pytest.mark.anyio
    async def test_create_melding(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") > 0
        assert data.get("text") == "This is a test melding."
        assert data.get("state") == MeldingStates.NEW
        assert data.get("classification", "") is None
        assert data.get("token") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.anyio
    @pytest.mark.parametrize("classification_name,", ["classification_name"], indirect=True)
    async def test_create_melding_with_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "classification_name"})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") is not None
        assert data.get("text") == "classification_name"
        assert data.get("state") == MeldingStates.CLASSIFIED
        assert data.get("classification") == classification.id

    @pytest.mark.anyio
    async def test_create_melding_text_minimum_length_violation(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": ""})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "string_too_short"
        assert violation.get("loc") == ["body", "text"]
        assert violation.get("msg") == "String should have at least 1 character"


class TestMeldingList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "melding:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_meldingen_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert response.headers.get("content-range") == f"melding {offset}-{limit - 1 + offset}/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                ],
            ),
            (
                "text",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                ],
            ),
            (
                "text",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_meldingen_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["text"] == expected[i]["text"]
            assert data[i]["state"] == expected[i]["state"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "melding 0-49/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "text",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                ],
            ),
            (
                3,
                1,
                "text",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_meldingen_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["text"] == expected[i]["text"]
            assert data[i]["state"] == expected[i]["state"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"melding {offset}-{limit - 1 + offset}/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_locations",
        [
            (
                "POINT(52.37256509259712 4.898451690545197)",  # Barndesteeg 1B, Stadsdeel: Centrum
                "POINT(52.40152495315581 4.938320969227033)",  # Bakkerswaal 30, Stadsdeel: Noord
                "POINT(52.3341878625198 4.872746743968191)",  # Ennemaborg 7, Stadsdeel: Zuid
                "POINT(52.37127670396132 4.7765014635225835)",  # Osdorperweg 686, Stadsdeel: Nieuw-West
            )
        ],
    )
    async def test_list_in_area_filter(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        meldingen_with_location: list[Melding],
    ) -> None:
        geojson = """{
            "type": "Feature",
            "id": "stadsdelen.03630000000018.3",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            4.932968460535252,
                            52.37040621658548
                        ],
                        [
                            4.93295630985113,
                            52.370405495894914
                        ],
                        [
                            4.93289788563862,
                            52.37036515069431
                        ],
                        [
                            4.932914424644401,
                            52.37004775993005
                        ],
                        [
                            4.932945026033431,
                            52.369902842965374
                        ],
                        [
                            4.932892122175176,
                            52.36940094704014
                        ],
                        [
                            4.932820425048245,
                            52.3690696462181
                        ],
                        [
                            4.93268606363202,
                            52.36869801069106
                        ],
                        [
                            4.932585315211286,
                            52.3684967399572
                        ],
                        [
                            4.932088278827758,
                            52.36766674921066
                        ],
                        [
                            4.932110847644505,
                            52.36766231514913
                        ],
                        [
                            4.932104766756013,
                            52.36763533767654
                        ],
                        [
                            4.932122774157019,
                            52.36760036386494
                        ],
                        [
                            4.932185166131545,
                            52.36756837377988
                        ],
                        [
                            4.931984238335891,
                            52.367234463484216
                        ],
                        [
                            4.931581869815988,
                            52.36656743072131
                        ],
                        [
                            4.927509034451039,
                            52.36649948693886
                        ],
                        [
                            4.927315069329468,
                            52.366486393572366
                        ],
                        [
                            4.927132927492587,
                            52.366458767780905
                        ],
                        [
                            4.926983909083487,
                            52.36642408030555
                        ],
                        [
                            4.926848945508368,
                            52.3663819695236
                        ],
                        [
                            4.926721939648305,
                            52.36633140514704
                        ],
                        [
                            4.926597711550381,
                            52.366269284267865
                        ],
                        [
                            4.925597673983138,
                            52.36566507394923
                        ],
                        [
                            4.924773594305595,
                            52.36524703066644
                        ],
                        [
                            4.922307895214352,
                            52.36375732377905
                        ],
                        [
                            4.922196321957743,
                            52.363682521307894
                        ],
                        [
                            4.922062122288712,
                            52.3636149817817
                        ],
                        [
                            4.921913284674311,
                            52.36356013813241
                        ],
                        [
                            4.921760834910865,
                            52.363520774903776
                        ],
                        [
                            4.921480419027592,
                            52.36347755574364
                        ],
                        [
                            4.921100631036134,
                            52.363431023728324
                        ],
                        [
                            4.920382910934627,
                            52.363370333032904
                        ],
                        [
                            4.920207997214749,
                            52.3633354899138
                        ],
                        [
                            4.920041768931642,
                            52.363287289119285
                        ],
                        [
                            4.919872863424811,
                            52.363220104465086
                        ],
                        [
                            4.919714758043161,
                            52.36313535528916
                        ],
                        [
                            4.919024542047929,
                            52.362552947382405
                        ],
                        [
                            4.918867971241932,
                            52.36245532372946
                        ],
                        [
                            4.918702732106644,
                            52.36237228857123
                        ],
                        [
                            4.918421906316832,
                            52.362266002709596
                        ],
                        [
                            4.918125970622663,
                            52.36219069987024
                        ],
                        [
                            4.917804821970703,
                            52.362143796362645
                        ],
                        [
                            4.917485240407887,
                            52.36212920903002
                        ],
                        [
                            4.916409875786401,
                            52.362087836239716
                        ],
                        [
                            4.916236470598368,
                            52.36206654669183
                        ],
                        [
                            4.916000291789961,
                            52.362027121504724
                        ],
                        [
                            4.915776702458771,
                            52.36197869534833
                        ],
                        [
                            4.915075296083733,
                            52.36178535167643
                        ],
                        [
                            4.914031444951801,
                            52.36149497935785
                        ],
                        [
                            4.912846254958975,
                            52.36135773050104
                        ],
                        [
                            4.911776148029735,
                            52.361247041291584
                        ],
                        [
                            4.911622523817606,
                            52.36122020707672
                        ],
                        [
                            4.911487314515318,
                            52.361179192138465
                        ],
                        [
                            4.911365995687501,
                            52.36112426596109
                        ],
                        [
                            4.911284955647415,
                            52.36107391455815
                        ],
                        [
                            4.911199706029659,
                            52.36100270365169
                        ],
                        [
                            4.91108432984944,
                            52.36092487340264
                        ],
                        [
                            4.910832772017304,
                            52.360794240532215
                        ],
                        [
                            4.910560410547325,
                            52.360695312928385
                        ],
                        [
                            4.910252562988866,
                            52.36062277348205
                        ],
                        [
                            4.909955261111934,
                            52.36058533684385
                        ],
                        [
                            4.909638838075353,
                            52.36057726609801
                        ],
                        [
                            4.909350439644787,
                            52.36059786161905
                        ],
                        [
                            4.909032882633744,
                            52.36065006532274
                        ],
                        [
                            4.908805064079055,
                            52.36065892355779
                        ],
                        [
                            4.908561896801273,
                            52.36063990230096
                        ],
                        [
                            4.9083218238709,
                            52.360589912384
                        ],
                        [
                            4.907968697031695,
                            52.36049784223509
                        ],
                        [
                            4.907778807841849,
                            52.36042974636007
                        ],
                        [
                            4.907640674120677,
                            52.36036918483935
                        ],
                        [
                            4.907505171197005,
                            52.360298873148906
                        ],
                        [
                            4.907374490887242,
                            52.3602184067455
                        ],
                        [
                            4.907098760595616,
                            52.36000312038495
                        ],
                        [
                            4.906916740590622,
                            52.359875610218005
                        ],
                        [
                            4.906636857307591,
                            52.3597229413562
                        ],
                        [
                            4.906499983746122,
                            52.359662940839264
                        ],
                        [
                            4.906166496468341,
                            52.359549095851385
                        ],
                        [
                            4.905970177639016,
                            52.359497849863224
                        ],
                        [
                            4.905158070599037,
                            52.35934703025795
                        ],
                        [
                            4.904629105794884,
                            52.35921067042974
                        ],
                        [
                            4.903995387767107,
                            52.359047393858226
                        ],
                        [
                            4.901669430627513,
                            52.35859366741457
                        ],
                        [
                            4.899241434985725,
                            52.35809888591999
                        ],
                        [
                            4.899000757695877,
                            52.35804731064258
                        ],
                        [
                            4.898755431977134,
                            52.35800466747462
                        ],
                        [
                            4.89850638068407,
                            52.35797112197672
                        ],
                        [
                            4.898254497797116,
                            52.357946794659036
                        ],
                        [
                            4.898033646974922,
                            52.35793319157717
                        ],
                        [
                            4.896172125904802,
                            52.35804521925908
                        ],
                        [
                            4.89087471689635,
                            52.35836786979492
                        ],
                        [
                            4.890649402141683,
                            52.358395056514134
                        ],
                        [
                            4.890432124622291,
                            52.35843073399282
                        ],
                        [
                            4.890210438879305,
                            52.3584772497516
                        ],
                        [
                            4.890003090885578,
                            52.3585306649837
                        ],
                        [
                            4.889802019731908,
                            52.35859243785884
                        ],
                        [
                            4.889600221106837,
                            52.35866536111592
                        ],
                        [
                            4.889399639719445,
                            52.35875010802157
                        ],
                        [
                            4.889247776029476,
                            52.35882605381408
                        ],
                        [
                            4.888926003679249,
                            52.35901732502429
                        ],
                        [
                            4.88863898937914,
                            52.35922831703927
                        ],
                        [
                            4.888406697132107,
                            52.3594395299535
                        ],
                        [
                            4.888287028265705,
                            52.359582883362236
                        ],
                        [
                            4.888170228497821,
                            52.35970340192004
                        ],
                        [
                            4.887945324574723,
                            52.35989425189675
                        ],
                        [
                            4.887680381537773,
                            52.36007242157568
                        ],
                        [
                            4.88738383212161,
                            52.3602308190204
                        ],
                        [
                            4.886295040485301,
                            52.360777938129836
                        ],
                        [
                            4.885380621576583,
                            52.36123480369442
                        ],
                        [
                            4.884399213984411,
                            52.361724991835935
                        ],
                        [
                            4.884230227489495,
                            52.36179194264265
                        ],
                        [
                            4.884040454664786,
                            52.36184703992029
                        ],
                        [
                            4.883840351950255,
                            52.36188608581908
                        ],
                        [
                            4.883633509557181,
                            52.36190838552705
                        ],
                        [
                            4.882629516081476,
                            52.36192620246715
                        ],
                        [
                            4.882505569973379,
                            52.36193611787314
                        ],
                        [
                            4.882392531903928,
                            52.36195504942261
                        ],
                        [
                            4.882254985888854,
                            52.361992516894496
                        ],
                        [
                            4.882094053879826,
                            52.36205440296905
                        ],
                        [
                            4.881957783762783,
                            52.36211772426494
                        ],
                        [
                            4.881847520421957,
                            52.36218428415488
                        ],
                        [
                            4.881742961658096,
                            52.36227843368016
                        ],
                        [
                            4.881710765868534,
                            52.362320987950476
                        ],
                        [
                            4.881654481492354,
                            52.3624148132364
                        ],
                        [
                            4.881615102894421,
                            52.36250792876208
                        ],
                        [
                            4.88157095129861,
                            52.36276349515128
                        ],
                        [
                            4.88151145572692,
                            52.362936758211724
                        ],
                        [
                            4.881407358423821,
                            52.363125433394494
                        ],
                        [
                            4.881230791317293,
                            52.3632679164003
                        ],
                        [
                            4.881116087099424,
                            52.36336049408741
                        ],
                        [
                            4.880845651465425,
                            52.363541015741134
                        ],
                        [
                            4.880702857001317,
                            52.363624862631085
                        ],
                        [
                            4.880537267590781,
                            52.36370818937204
                        ],
                        [
                            4.880254584071623,
                            52.363823091749765
                        ],
                        [
                            4.880057024742048,
                            52.36388644499252
                        ],
                        [
                            4.879775013891519,
                            52.36396157839293
                        ],
                        [
                            4.879598584151693,
                            52.36403740653011
                        ],
                        [
                            4.879491016376753,
                            52.36410759783738
                        ],
                        [
                            4.879415215022311,
                            52.36417688272536
                        ],
                        [
                            4.87935416023422,
                            52.36425715091801
                        ],
                        [
                            4.879311448836154,
                            52.36434200961499
                        ],
                        [
                            4.879258354480822,
                            52.364484821582835
                        ],
                        [
                            4.879225186657601,
                            52.36462987608043
                        ],
                        [
                            4.879212148451086,
                            52.364776122430555
                        ],
                        [
                            4.879219447962378,
                            52.364923354814294
                        ],
                        [
                            4.879226364021048,
                            52.36498610986451
                        ],
                        [
                            4.879213572819729,
                            52.365124879472454
                        ],
                        [
                            4.879180119869668,
                            52.36525887780854
                        ],
                        [
                            4.879131002523114,
                            52.365379920504594
                        ],
                        [
                            4.879064278704902,
                            52.36549988997383
                        ],
                        [
                            4.878954378664493,
                            52.36566178157328
                        ],
                        [
                            4.878811587931855,
                            52.36583279818445
                        ],
                        [
                            4.878695247149822,
                            52.365945445072924
                        ],
                        [
                            4.878528816181828,
                            52.36607931237841
                        ],
                        [
                            4.878391847129671,
                            52.36617132438654
                        ],
                        [
                            4.878131472073651,
                            52.36630815775432
                        ],
                        [
                            4.877883729767059,
                            52.36646479992514
                        ],
                        [
                            4.877720339166566,
                            52.36658668055412
                        ],
                        [
                            4.877512719943062,
                            52.366770260060015
                        ],
                        [
                            4.877425287046978,
                            52.36695157954874
                        ],
                        [
                            4.877343591207875,
                            52.367181718051555
                        ],
                        [
                            4.877313920452709,
                            52.36729899696452
                        ],
                        [
                            4.877259838006703,
                            52.3677006143279
                        ],
                        [
                            4.877193148313909,
                            52.36789605280308
                        ],
                        [
                            4.877082757132627,
                            52.36810592598219
                        ],
                        [
                            4.876803575784635,
                            52.36850153089915
                        ],
                        [
                            4.876673890334636,
                            52.36867544150224
                        ],
                        [
                            4.876297120630309,
                            52.368964892758484
                        ],
                        [
                            4.875987329082795,
                            52.369251989637284
                        ],
                        [
                            4.875800551176549,
                            52.36946012067378
                        ],
                        [
                            4.875668717586297,
                            52.36963764293675
                        ],
                        [
                            4.875039284205583,
                            52.370681578272745
                        ],
                        [
                            4.87449761284353,
                            52.371887264729736
                        ],
                        [
                            4.874446105566979,
                            52.37205832967524
                        ],
                        [
                            4.874434239913924,
                            52.3721993944968
                        ],
                        [
                            4.874477637365231,
                            52.372322156965105
                        ],
                        [
                            4.874549856326817,
                            52.37244782141119
                        ],
                        [
                            4.874639657486876,
                            52.37256038592442
                        ],
                        [
                            4.874777300138244,
                            52.37268828375405
                        ],
                        [
                            4.874825084181699,
                            52.372725079549035
                        ],
                        [
                            4.875162798658754,
                            52.372922167174
                        ],
                        [
                            4.8752297505393,
                            52.37297261714721
                        ],
                        [
                            4.875290221556971,
                            52.37303368950924
                        ],
                        [
                            4.875378471796294,
                            52.37314857455321
                        ],
                        [
                            4.875426039269469,
                            52.37323349839517
                        ],
                        [
                            4.875481453021743,
                            52.37340840520902
                        ],
                        [
                            4.875470660365082,
                            52.373758376244275
                        ],
                        [
                            4.875508225576382,
                            52.37407520282488
                        ],
                        [
                            4.875535240217038,
                            52.37421189690756
                        ],
                        [
                            4.875847238512531,
                            52.374182470777185
                        ],
                        [
                            4.875881608679822,
                            52.374315583478
                        ],
                        [
                            4.875988435950932,
                            52.37453653138919
                        ],
                        [
                            4.876586362591042,
                            52.375487315237834
                        ],
                        [
                            4.878008170232285,
                            52.37776051603215
                        ],
                        [
                            4.877903151376969,
                            52.377784663751285
                        ],
                        [
                            4.878072605536509,
                            52.37804772567949
                        ],
                        [
                            4.878095152501521,
                            52.37804229517866
                        ],
                        [
                            4.878288173785453,
                            52.37835072019298
                        ],
                        [
                            4.878093987819444,
                            52.378398338210246
                        ],
                        [
                            4.878160440681746,
                            52.37850478669259
                        ],
                        [
                            4.879855645095213,
                            52.38121873574942
                        ],
                        [
                            4.879866288432046,
                            52.381282072738536
                        ],
                        [
                            4.879847727613653,
                            52.38133949652995
                        ],
                        [
                            4.879625886616115,
                            52.381586184003176
                        ],
                        [
                            4.879576551660764,
                            52.381681125319616
                        ],
                        [
                            4.879566301369832,
                            52.38173744324941
                        ],
                        [
                            4.879571664849801,
                            52.38180778600762
                        ],
                        [
                            4.879590823622529,
                            52.38186369073811
                        ],
                        [
                            4.879632539834333,
                            52.381930090919184
                        ],
                        [
                            4.879698912029771,
                            52.38199816959845
                        ],
                        [
                            4.879803848379316,
                            52.38206673703616
                        ],
                        [
                            4.88009629879849,
                            52.38218305923548
                        ],
                        [
                            4.880327283093425,
                            52.382304510252446
                        ],
                        [
                            4.880480214411756,
                            52.382410878042876
                        ],
                        [
                            4.880644835769898,
                            52.38256371709733
                        ],
                        [
                            4.880754773652159,
                            52.38270772983052
                        ],
                        [
                            4.881661305445451,
                            52.384178781651634
                        ],
                        [
                            4.881825820848609,
                            52.38443463547443
                        ],
                        [
                            4.882345352144394,
                            52.38518504986405
                        ],
                        [
                            4.88258544716241,
                            52.3854603774945
                        ],
                        [
                            4.883033749270839,
                            52.38600134156098
                        ],
                        [
                            4.883233452204851,
                            52.386242315662045
                        ],
                        [
                            4.883996254328669,
                            52.38734197631695
                        ],
                        [
                            4.884478944064861,
                            52.38837845496537
                        ],
                        [
                            4.885745414969803,
                            52.388166519774266
                        ],
                        [
                            4.885971400990136,
                            52.388128703521225
                        ],
                        [
                            4.891009186541242,
                            52.388439832566995
                        ],
                        [
                            4.892069460658826,
                            52.38850528726725
                        ],
                        [
                            4.89220795074676,
                            52.38818989525936
                        ],
                        [
                            4.89230313610152,
                            52.38820596755932
                        ],
                        [
                            4.892295646569671,
                            52.38822156583984
                        ],
                        [
                            4.892309292613816,
                            52.38835716607374
                        ],
                        [
                            4.892361202478646,
                            52.388523295551224
                        ],
                        [
                            4.89507756612656,
                            52.388690927433494
                        ],
                        [
                            4.895655366751776,
                            52.386921298015004
                        ],
                        [
                            4.895872000887692,
                            52.38636072748414
                        ],
                        [
                            4.896241214121421,
                            52.38564782775286
                        ],
                        [
                            4.896758331297671,
                            52.38488554989845
                        ],
                        [
                            4.897306139281555,
                            52.384269913924044
                        ],
                        [
                            4.897909804452803,
                            52.38367433300873
                        ],
                        [
                            4.898658978364492,
                            52.38304298516724
                        ],
                        [
                            4.898767369578588,
                            52.382968789527766
                        ],
                        [
                            4.89947456809518,
                            52.382484634478956
                        ],
                        [
                            4.900054632457789,
                            52.38215406417093
                        ],
                        [
                            4.900362427082374,
                            52.38197864096158
                        ],
                        [
                            4.901178919444601,
                            52.381561991114495
                        ],
                        [
                            4.902091453985454,
                            52.38119473897674
                        ],
                        [
                            4.902258006102835,
                            52.38112770788837
                        ],
                        [
                            4.903258239544371,
                            52.3807734156008
                        ],
                        [
                            4.904307767808268,
                            52.380463023031794
                        ],
                        [
                            4.905470102585821,
                            52.380202979769145
                        ],
                        [
                            4.906000152241058,
                            52.380105650087
                        ],
                        [
                            4.906404284335824,
                            52.38003991987597
                        ],
                        [
                            4.906525474620136,
                            52.38001876950403
                        ],
                        [
                            4.907617069027481,
                            52.37988355361613
                        ],
                        [
                            4.908679627270213,
                            52.379855280661225
                        ],
                        [
                            4.910588379883426,
                            52.37991295880227
                        ],
                        [
                            4.911152992110621,
                            52.3776356468315
                        ],
                        [
                            4.911979308355755,
                            52.37757900896053
                        ],
                        [
                            4.912080956283912,
                            52.377183652939465
                        ],
                        [
                            4.912033070244817,
                            52.37711056164602
                        ],
                        [
                            4.911900032310929,
                            52.37709808308859
                        ],
                        [
                            4.911975562428193,
                            52.37679649871029
                        ],
                        [
                            4.912077425811955,
                            52.37680446611395
                        ],
                        [
                            4.912086317415093,
                            52.37678464798218
                        ],
                        [
                            4.912116200994428,
                            52.376773865811536
                        ],
                        [
                            4.912399269554342,
                            52.37678894106044
                        ],
                        [
                            4.912724055730656,
                            52.37679623767947
                        ],
                        [
                            4.913297947652179,
                            52.376785171118584
                        ],
                        [
                            4.913554871150196,
                            52.376770443640275
                        ],
                        [
                            4.91411151172191,
                            52.37671485102139
                        ],
                        [
                            4.91450636566573,
                            52.37665854715755
                        ],
                        [
                            4.920496101696215,
                            52.37568610154727
                        ],
                        [
                            4.921242641850312,
                            52.375574978798596
                        ],
                        [
                            4.921256497459452,
                            52.37560923146968
                        ],
                        [
                            4.921274897667978,
                            52.37560649072492
                        ],
                        [
                            4.921286897964106,
                            52.375621646244426
                        ],
                        [
                            4.921406331416486,
                            52.37560373629046
                        ],
                        [
                            4.921560152364059,
                            52.37558215965221
                        ],
                        [
                            4.921538664965106,
                            52.37552926350509
                        ],
                        [
                            4.923031735541689,
                            52.37530096041513
                        ],
                        [
                            4.923511184280137,
                            52.37520930398512
                        ],
                        [
                            4.92404356335214,
                            52.375079025852855
                        ],
                        [
                            4.924252911967428,
                            52.375018881030634
                        ],
                        [
                            4.924927419418552,
                            52.37480309741382
                        ],
                        [
                            4.927693150141727,
                            52.37391337706667
                        ],
                        [
                            4.927902306357344,
                            52.373852362239816
                        ],
                        [
                            4.928546109165322,
                            52.37367988542281
                        ],
                        [
                            4.929397720261254,
                            52.37347367803875
                        ],
                        [
                            4.929850504368508,
                            52.37334436930098
                        ],
                        [
                            4.930185830929428,
                            52.373224348206534
                        ],
                        [
                            4.93054606272745,
                            52.37307559870417
                        ],
                        [
                            4.930874933287612,
                            52.37291900682892
                        ],
                        [
                            4.931173081862585,
                            52.372749542198314
                        ],
                        [
                            4.931427313834028,
                            52.37258514760521
                        ],
                        [
                            4.931744016016384,
                            52.37234875872986
                        ],
                        [
                            4.931969307237153,
                            52.37215513153936
                        ],
                        [
                            4.932101226933067,
                            52.371982284123604
                        ],
                        [
                            4.932175086441269,
                            52.37195670141342
                        ],
                        [
                            4.932254057438534,
                            52.37196104033416
                        ],
                        [
                            4.9323916873352,
                            52.37178391841722
                        ],
                        [
                            4.93232738270253,
                            52.371748403714186
                        ],
                        [
                            4.932315743384203,
                            52.37173071616818
                        ],
                        [
                            4.932319959261071,
                            52.371697630708525
                        ],
                        [
                            4.932502388212156,
                            52.37150339742618
                        ],
                        [
                            4.93262340762388,
                            52.37127760602099
                        ],
                        [
                            4.932763258156032,
                            52.37090199906483
                        ],
                        [
                            4.932773746671734,
                            52.37072957454311
                        ],
                        [
                            4.932812192218064,
                            52.37069196480178
                        ],
                        [
                            4.932844438707763,
                            52.370681833591306
                        ],
                        [
                            4.93289063305359,
                            52.370681902991265
                        ],
                        [
                            4.932895048098046,
                            52.3706637288471
                        ],
                        [
                            4.932910012404377,
                            52.37066500858801
                        ],
                        [
                            4.932937386878123,
                            52.370545604301014
                        ],
                        [
                            4.932968460535252,
                            52.37040621658548
                        ]
                    ]
                ]
            },
            "properties": {
                "identificatie": "03630000000018",
                "volgnummer": 3,
                "registratiedatum": "2024-01-25T20:36:51",
                "naam": "Centrum",
                "code": "A",
                "beginGeldigheid": "2015-01-01T00:00:00",
                "eindGeldigheid": null,
                "documentdatum": "2015-06-23",
                "documentnummer": "3B/2015/134",
                "ligtInGemeenteId": "0363"
            },
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4326"
                }
            }
        }"""

        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"in_area": geojson})

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

        melding = meldingen_with_location[0]
        melding_response = body[0]

        assert melding_response.get("text") == melding.text


class TestMeldingRetrieve(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "melding:retrieve"
    METHOD: Final[str] = "GET"
    PATH_PARAMS: dict[str, Any] = {"melding_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_text", ["Er ligt poep op de stoep.", "Er is een matras naast de prullenbak gedumpt."], indirect=True
    )
    async def test_retrieve_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=melding.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == melding.text
        assert body.get("state") == MeldingStates.NEW
        assert body.get("classification", "") is None
        assert body.get("geo_location", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_retrieve_melding_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class BaseTokenAuthenticationTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @abstractmethod
    def get_method(self) -> str: ...

    def get_json(self) -> dict[str, Any] | None:
        return None

    def get_extra_path_params(self) -> dict[str, Any]:
        return {}

    @pytest.mark.anyio
    async def test_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1, **self.get_extra_path_params()),
            json=self.get_json(),
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_token_invalid(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id, **self.get_extra_path_params()),
            params={"token": ""},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_token_expired(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id, **self.get_extra_path_params()),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestMeldingUpdate(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:update"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "PATCH"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"text": "classification_name"}

    @pytest.mark.anyio
    async def test_update_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), params={"token": ""}, json=self.get_json()
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_update_melding_classification_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "classification_name")],
        indirect=True,
    )
    async def test_update_melding(
        self, app: FastAPI, client: AsyncClient, melding: Melding, classification: Classification
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == "classification_name"
        assert body.get("state") == MeldingStates.CLASSIFIED
        assert body.get("classification") == classification.id
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()


class TestMeldingAnswerQuestions(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:answer_questions"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification")],
        indirect=True,
    )
    async def test_answer_questions(
        self, app: FastAPI, client: AsyncClient, melding_with_classification: Melding, form_with_classification: Form
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_classification.created_at.isoformat()
        assert body.get("updated_at") == melding_with_classification.updated_at.isoformat()

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "is_required"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification", True)],
        indirect=True,
    )
    async def test_answer_questions_with_required_answered(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_answers: Melding,
    ) -> None:

        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_answers.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_answers.created_at.isoformat()
        assert body.get("updated_at") == melding_with_answers.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_answer_questions_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.PROCESSING, "supersecrettoken")],
        indirect=True,
    )
    async def test_answer_questions_wrong_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "is_required", "classification_name"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.CLASSIFIED,
                "supersecrettoken",
                True,
                "test_classification",
            )
        ],
        indirect=["is_required", "classification_name"],
    )
    async def test_answer_questions_without_answering_required_questions(
        self, app: FastAPI, client: AsyncClient, melding_with_classification: Melding, form_with_classification: Form
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "All required questions must be answered first"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "is_required"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification", True)],
        indirect=True,
    )
    async def test_answer_questions_with_some_required_answered(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_some_answers: Melding,
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_some_answers.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "All required questions must be answered first"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification")],
        indirect=True,
    )
    async def test_answer_questions_with_no_form_for_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_classification.created_at.isoformat()
        assert body.get("updated_at") == melding_with_classification.updated_at.isoformat()


class TestMeldingAddAttachments(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-attachments"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.LOCATION_SUBMITTED, "supersecrettoken")],
        indirect=True,
    )
    async def test_add_attachments(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.ATTACHMENTS_ADDED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_add_attachments_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=1), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.PROCESSING, "supersecrettoken")],
        indirect=True,
    )
    async def test_add_attachments_wrong_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingSubmitLocation(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:submit-location"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_geo_location"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.QUESTIONS_ANSWERED,
                "supersecrettoken",
                "POINT(52.3680 4.8970)",
            )
        ],
        indirect=True,
    )
    async def test_submit_location(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.LOCATION_SUBMITTED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.QUESTIONS_ANSWERED, "supersecrettoken")],
        indirect=True,
    )
    async def test_submit_location_no_location_added(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Location must be added before submitting"}

    @pytest.mark.anyio
    async def test_submit_location_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestMeldingProcess(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:process"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.SUBMITTED)], indirect=True
    )
    async def test_process_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.PROCESSING
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_process_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_process_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingComplete(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:complete"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.PROCESSING)], indirect=True
    )
    async def test_complete_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.COMPLETED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_complete_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_complete_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingQuestionAnswer:
    ROUTE_NAME_CREATE: Final[str] = "melding:answer-question"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"==":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"==":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question_without_component(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
        db_session: AsyncSession,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        await db_session.delete(panel_components[0])
        await db_session.commit()

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"!=":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question_invalid_input(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
        body = response.json()
        detail = body.get("detail")
        assert detail == "Invalid input"

    @pytest.mark.anyio
    async def test_answer_question_melding_does_not_exists(
        self,
        app: FastAPI,
        client: AsyncClient,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=999, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"

    @pytest.mark.anyio
    async def test_answer_question_unauthorized_token_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_answer_question_token_missing(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            json=data,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_answer_question_melding_not_classified(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Melding not classified"

    @pytest.mark.anyio
    async def test_answer_question_does_not_exists(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
    ) -> None:
        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=999),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "test_classification")],
        indirect=[
            "classification_name",
        ],
    )
    async def test_answer_question_not_connected_to_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        db_session: AsyncSession,
    ) -> None:
        question = Question(text="is dit een vraag?")
        db_session.add(question)
        await db_session.commit()

        data = {"text": "Ja, dit is een vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"


class TestMeldingUploadAttachment:
    ROUTE_NAME_CREATE: Final[str] = "melding:attachment"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "filename"],
        [
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.jpg"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.png"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.webp"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam logo.webp"),
        ],
    )
    async def test_upload_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
        malware_scanner_override: BaseMalwareScanner,
        filename: str,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        filename,
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_200_OK

        await db_session.refresh(melding)
        attachments = await melding.awaitable_attrs.attachments
        assert len(attachments) == 1

        await db_session.refresh(attachments[0])

        assert attachments[0].original_filename == filename

        split_path, _ = attachments[0].file_path.rsplit(".", 1)
        optimized_path = f"{split_path}-optimized.webp"
        assert attachments[0].optimized_path == optimized_path

        thumbnail_path = f"{split_path}-thumbnail.webp"
        assert attachments[0].thumbnail_path == thumbnail_path

        blob_client = container_client.get_blob_client(attachments[0].file_path)
        async with blob_client:
            assert await blob_client.exists() is True
            properties = await blob_client.get_blob_properties()

        assert properties.size == path.getsize(
            path.join(
                path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                "resources",
                filename,
            )
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_too_large(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "too-large.jpg",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert response.json().get("detail") == "Allowed content size exceeded"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "filename"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "test_file.txt")],
    )
    async def test_upload_attachment_media_type_not_allowed(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        filename: str,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        filename,
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        body = response.json()
        assert body.get("detail") == "Attachment not allowed"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_media_type_integrity_validation_fails(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": (
                    "amsterdam-logo.png",
                    open(
                        path.join(
                            path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                            "resources",
                            "amsterdam-logo.png",
                        ),
                        "rb",
                    ),
                    "image/jpeg",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        body = response.json()
        assert body.get("detail") == "Media type of data does not match provided media type"

        await db_session.refresh(melding)
        attachments = await melding.awaitable_attrs.attachments
        assert len(attachments) == 0

    @pytest.mark.anyio
    async def test_upload_attachment_melding_not_found(
        self, app: FastAPI, client: AsyncClient, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=123),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_token_missing(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_upload_attachment_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_upload_attachment_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestMeldingDownloadAttachment(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachment-download"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    @override
    def get_extra_path_params(self) -> dict[str, Any]:
        return {"attachment_id": 456}

    @pytest.mark.anyio
    async def test_download_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_download_attachment_attached_to_other_melding(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, db_session: AsyncSession
    ) -> None:
        melding = Melding(text="Hoi!", token="supersecuretoken")

        db_session.add(melding)
        await db_session.commit()

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, container_client: ContainerClient
    ) -> None:
        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/jpeg"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_optimized_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "optimized"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_optimized_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        db_session: AsyncSession,
    ) -> None:
        attachment.optimized_path = f"/tmp/{uuid4()}/optimized.webp"
        attachment.optimized_media_type = "image/webp"
        db_session.add(attachment)
        await db_session.commit()

        blob_client = container_client.get_blob_client(attachment.optimized_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "optimized"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/webp"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_thumbnail_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "thumbnail"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_thumbnail_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        db_session: AsyncSession,
    ) -> None:
        attachment.thumbnail_path = f"/tmp/{uuid4()}/thumbnail.webp"
        attachment.thumbnail_media_type = "image/webp"
        db_session.add(attachment)
        await db_session.commit()

        blob_client = container_client.get_blob_client(attachment.thumbnail_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "thumbnail"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/webp"


class TestMeldingListAttachments(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "melding:attachments"
    PATH_PARAMS: dict[str, Any] = {"melding_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecuretoken",)])
    async def test_list_attachments(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id))

        assert response.status_code == HTTP_200_OK

        attachments = await melding_with_attachments.awaitable_attrs.attachments
        body = response.json()

        assert len(attachments) == len(body)

    @pytest.mark.anyio
    async def test_list_attachments_with_non_existing_melding(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=123))

        assert response.status_code == HTTP_200_OK
        body = response.json()

        assert len(body) == 0


class TestMelderMeldingListAttachments(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachments_melder"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_melder_list_attachments_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecuretoken",)])
    async def test_melder_list_attachments(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK

        attachments = await melding_with_attachments.awaitable_attrs.attachments
        body = response.json()

        assert len(attachments) == len(body)


class TestMeldingDeleteAttachmentAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachment-delete"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "DELETE"

    @override
    def get_extra_path_params(self) -> dict[str, Any]:
        return {"attachment_id": 456}

    @pytest.mark.anyio
    async def test_delete_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_delete_attachment_attached_to_other_melding(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, db_session: AsyncSession
    ) -> None:
        melding = Melding(text="Hoi!", token="supersecuretoken")

        db_session.add(melding)
        await db_session.commit()

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, container_client: ContainerClient
    ) -> None:
        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK

        async with blob_client:
            assert await blob_client.exists() is False


class TestAddLocationToMeldingAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:location-add"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "POST"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [52.3680605, 4.897092]},
            "properties": {},
        }

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_add_location_to_melding(
        self, app: FastAPI, client: AsyncClient, melding: Melding, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=geojson,
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("geo_location").get("type") == geojson["type"]
        assert body.get("geo_location").get("geometry").get("type") == geojson["geometry"]["type"]
        assert body.get("geo_location").get("geometry").get("coordinates") == geojson["geometry"]["coordinates"]

    @pytest.mark.anyio
    async def test_add_location_to_melding_melding_not_found(
        self, app: FastAPI, client: AsyncClient, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=123),
            params={"token": "test"},
            json=geojson,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "geojson_geometry"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                {
                    "type": "Polygon",
                    "coordinates": [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]]],
                },
            )
        ],
        indirect=True,
    )
    async def test_add_location_wrong_geometry_type(
        self, app: FastAPI, client: AsyncClient, melding: Melding, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecrettoken"},
            json=geojson,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")

        assert len(detail) == 6
        assert detail[0].get("msg") == "Input should be 'Point'"


class TestMeldingAddContactAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:contact-add"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "POST"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"email": "user@example.com", "phone": "+31612345678"}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "email", "phone"],
        [
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "melder@example.com", "+31612345678"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", None, "+31612345678"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "melder@example.com", None),
        ],
    )
    async def test_add_contact(
        self, app: FastAPI, client: AsyncClient, melding: Melding, email: str | None, phone: str | None
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json={"email": email, "phone": phone},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data.get("email") == email
        assert data.get("phone") == phone

    @pytest.mark.anyio
    async def test_add_contact_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=999),
            params={"token": "nonexistingtoken"},
            json={"email": "user@example.com", "phone": "+31612345678"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestMeldingContactInfoAdded(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-contact-info"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_email", "melding_phone"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                None,
                None,
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                "melder@example.com",
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                None,
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                "melder@example.com",
                None,
            ),
        ],
        indirect=True,
    )
    async def test_contact_info_added(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.CONTACT_INFO_ADDED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_contact_info_added_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestMeldingListQuestionsAnswers(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:answers"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers_melding_without_answers(
        self, app: FastAPI, client: AsyncClient, melding: Melding, auth_user: None
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers(
        self, app: FastAPI, client: AsyncClient, melding_with_answers: Melding, auth_user: None
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 10

        question_ids = []
        for answer_output in body:
            question = answer_output.get("question")
            question_ids.append(question.get("id"))

        assert sorted(question_ids) == question_ids

        answer = body[0]
        assert answer.get("id") > 0
        assert answer.get("text") == "Answer 0"
        assert answer.get("created_at") is not None
        assert answer.get("updated_at") is not None

        question = answer.get("question")
        assert question is not None
        assert question.get("id") > 0
        assert question.get("text") == "Question 0"
        assert question.get("created_at") is not None
        assert question.get("updated_at") is not None


class TestMelderMeldingListQuestionsAnswers(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:answers_melder"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_list_answers_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=999),
            params={"token": "nonexistingtoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers_melding_without_answers(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers(self, app: FastAPI, client: AsyncClient, melding_with_answers: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 10

        question_ids = []
        for answer_output in body:
            question = answer_output.get("question")
            question_ids.append(question.get("id"))

        assert sorted(question_ids) == question_ids

        answer = body[0]
        assert answer.get("id") > 0
        assert answer.get("text") == "Answer 0"
        assert answer.get("created_at") is not None
        assert answer.get("updated_at") is not None

        question = answer.get("question")
        assert question is not None
        assert question.get("id") > 0
        assert question.get("text") == "Question 0"
        assert question.get("created_at") is not None
        assert question.get("updated_at") is not None


class TestMelderMeldingRetrieve(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:retrieve_melder"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_token", ["supersecrettoken"])
    async def test_retrieve_melding(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == melding.text
        assert body.get("state") == MeldingStates.NEW
        assert body.get("classification", "") is None
        assert body.get("geo_location", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()


class TestMeldingSubmit(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:submit"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_state", "melding_token"],
        [(MeldingStates.CONTACT_INFO_ADDED, "supersecrettoken")],
    )
    async def test_submit_melding(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("state") == MeldingStates.SUBMITTED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_state", "melding_token"],
        [
            (MeldingStates.NEW, "supersecrettoken"),
            (MeldingStates.CLASSIFIED, "supersecrettoken"),
            (MeldingStates.QUESTIONS_ANSWERED, "supersecrettoken"),
            (MeldingStates.ATTACHMENTS_ADDED, "supersecrettoken"),
            (MeldingStates.LOCATION_SUBMITTED, "supersecrettoken"),
            (MeldingStates.SUBMITTED, "supersecrettoken"),
            (MeldingStates.PROCESSING, "supersecrettoken"),
            (MeldingStates.COMPLETED, "supersecrettoken"),
        ],
    )
    async def test_submit_melding_wrong_from_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "Transition not allowed from current state"
