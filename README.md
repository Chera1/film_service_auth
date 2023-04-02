# Authorization service

## Env parameters

```dotenv
SERVICE_HOST - service host
SERVICE_PORT - service port
DEBUG - flag is debug
REDIS_HOST - Redis host
REDIS_PORT - Redis port
PG_HOST - Postgres host
PG_PORT - Postgres port
PG_DB_NAME - Postgres database name
PG_USER - Postgres user
PG_PASSWORD - Postgres password
YANDEX_ID - Yandex auth service id
YANDEX_SECRET - Yandex auth service secret
VK_ID - VK auth service id
VK_SECRET - VK auth service secret
VK_AUTH_URL - VK auth service url (https://oauth.vk.com/authorize)
VK_TOKEN_URL - VK auth service url for token (https://oauth.vk.com/access_token)
VK_BASE_URL - VK auth service base url (https://oauth.vk.com/)
GOOGLE_ID - Google auth service id
GOOGLE_SECRET - Google auth service secret
MAIL_ID - Mail.ru auth service id
MAIL_SECRET - Mail.ru auth service secret
MAIL_PRIVATE - Mail.ru auth service key
```

## Local run
Firstly create an env file `src/core/.env` with above parameters

Before first run execute following command:
``` shell
cd src
flask db upgrade
```

To run service execute command:
```shell
python src/app.py
```

OpenApi documentation url:  http://localhost:5001/apidocs/

## Docker run
Create `.env` file in the root folder of project with above parameters:

To run service execute command:
```shell
docker compose up --build
```
OpenApi documentation url:  http://localhost/apidocs/

## SuperUser creating
To create a superUser execute following command:
```
cd src
flask create-user <login_example> <password_example> <example@email.com>
