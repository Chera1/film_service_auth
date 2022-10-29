from http import HTTPStatus
import pytest

from tests.functional.testdata.person_data import correct_id


pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    'url, query_data, expected_answer',
    [
        (
                '/api/v1/role/',
                {'page[size]': 60, "page[number]": -1},
                {'status': HTTPStatus.UNPROCESSABLE_ENTITY}
        ),
        (
                '/api/v1/role/',
                {},
                {'status': HTTPStatus.OK}
        )
    ]
)
async def test_role(make_get_request, query_data, expected_answer, url):

    # 1 Запрашиваем данные из ES по API
    body, status = await make_get_request(url, query_data)

    # 2. Проверяем ответ
    assert status == expected_answer['status']
    if hasattr(expected_answer, 'length'):
        assert len(body) == expected_answer['length']


async def test_role_id(check_cache, make_get_request):
    # 1. Запрашиваем данные из API
    body, status = await make_get_request('/api/v1/role/')
    assert status == HTTPStatus.OK
    person_id = body[0]['uuid']

    # 2. Запрашиваем данные из API по определенному id
    body, status = await make_get_request(f'/api/v1/persons/{person_id}')
    assert status == HTTPStatus.OK

    # 3. Если статус = 200, проверяем запись с person_id
    if status == HTTPStatus.OK:
        cache_response = await check_cache(f"/api/v1/persons/{person_id}?b''")
        assert cache_response['_source']['id'] == person_id
