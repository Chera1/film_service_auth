from datetime import timedelta

from flask_restful import Resource, request
from flask_security.utils import hash_password
from flask_jwt_extended import create_access_token, create_refresh_token, \
    jwt_required, get_jwt_identity
from flasgger import swag_from

from sqlalchemy.exc import IntegrityError

from src.db.db_postgres import db
from src.db.db_redis import jwt_redis_blocklist
from src.models.users import User
from src.models.authentication import Authentication
from src.models.roles import Role
from src.utils.db import SQLAlchemy
from src.utils.user_datastore import user_datastore
from src.utils.security import get_hash, check_password
from src.schemas.users import UserSchema
from src.utils.uuid_checker import is_uuid


ACCESS_EXPIRES = timedelta(hours=1)
user_schema = UserSchema()


class SignUp(Resource):
    """
    API-view для регистрации пользователя
    """
    def post(self):
        """
        User signup
        Provides user signup
        ---
        tags:
          - users
        parameters:
          - in: body
            name: login
            type: string
            required: true
          - in: body
            name: password
            type: string
            required: true
          - in: body
            name: email
            type: string
            required: true
          - in: body
            name: first_name
            type: string
            required: false
          - in: body
            name: last_name
            type: string
            required: false
          - in: body
            name: roles
            description: list of role IDs
            type: array
            required: false
            items:
              type: string
        responses:
          201:
            description: A single user item
            schema:
              id: User
              properties:
                user:
                  type: string
                  description: The name of the user
          400:
            description: Invalid credentials
        """
        try:
            data = request.get_json()
            if not data:
                return {'error': 'Credentials required'}, 400
            hash_ = get_hash(data["password"])
            data['password'] = hash_
            user_datastore.create_user(**data)
            db.session.commit()
            return {'user': data['login']}, 201
        except IntegrityError:
            return {'error': 'Login or email already exist'}, 400


class Login(Resource):
    """
    API-view для получения access- и refresh-токенов
    при вводе логина и пароля
    """
    def post(self):
        """
        User login
        Provides to get access and refresh tokens
        ---
        tags:
          - users
        parameters:
          - in: body
            name: login
            type: string
            required: true
          - in: body
            name: password
            type: string
            required: true
        responses:
          200:
            description: access and refresh token
            schema:
              properties:
                access_token:
                  type: string
                  description: access_token
                refresh_token:
                  type: string
                  description: refresh_token
          400:
            description: Invalid credentials
          401:
            description: Credentials required
        """
        data = request.get_json()
        user_agent = str(request.user_agent)
        if not data:
            return {'error': 'Credentials required'}, 400
        user = user_datastore.find_user(login=data['login'])

        if user and check_password(data['password'], user.password):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            auth_hist = Authentication(user_id=user.id, user_agent=user_agent)
            db.session.add(auth_hist)
            db.session.commit()
            # сохранять refresh-токен в базе
            return {'access_token': access_token, 'refresh_token': refresh_token}, 200
        return {'error': 'Invalid credentials'}, 401


class RefreshTokens(Resource):
    """
    API-view для получения новых access- и refresh-токенов
    с помощью refresh-токена
    """
    @jwt_required(refresh=True)
    def post(self):
        """
        Refresh tokens
        Provides to get new access and refresh tokens
        ---
        tags:
          - users
        parameters:
          - in: body
            name: refresh_token
            type: string
            required: true
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: new access and refresh token
            schema:
              properties:
                access_token:
                  type: string
                  description: access_token
                refresh_token:
                  type: string
                  description: refresh_token
          400:
            description: Token is invalid
        """
        try:
            identity = get_jwt_identity()
            access_token = create_access_token(identity=identity, fresh=False)
            refresh_token = create_refresh_token(identity=identity)
            # поместить старый refresh-токен в блок-лист
            # сохранять новый refresh-токен в базе
            # поместить старый access-токен в блок-лист
            return {'access_token': access_token, 'refresh_token': refresh_token}, 200
        except jwt.exceptions.DecodeError: #, InvalidSignatureError):
            return {'error': 'Token is invalid'}, 401


class Logout(Resource):
    """
    API-view для выхода пользователя из системы
    и помещения его access-токена в блок-лист
    """
    @jwt_required()
    def delete(self):
        jti = get_jwt()["jti"]
        jwt_redis_blocklist.set(jti, "", ex=ACCESS_EXPIRES)
        # поместить старый access-токен в блок-лист
        # поместить старый refresh-токен в блок-лист
        return {"msg": "User's token revoked"}, 200


class ChangeCreds(Resource):
    """API-view для изменения данных пользователя."""

    @jwt_required()
    def put(self, user_id):
        """
        Update user credentials
        Updates user credentials
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: uuid
            required: true
            default: all
          - in: body
            name: login
            type: string
            required: false
          - in: body
            name: password
            type: string
            required: false
          - in: body
            name: email
            type: string
            required: false
          - in: body
            name: first_name
            type: string
            required: false
          - in: body
            name: last_name
            type: string
            required: false
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: User credentials updated
            schema:
              properties:
                msg:
                  type: string
                  description: User updated
                result:
                  type: object
                  description: Updated user info
          400:
            description: Token is invalid
        """

        if not is_uuid(user_id):
            return {'error': 'Invalid UUID format'}, 400
        try:
            data = request.get_json()
            if not data:
                return {'msg': 'Empty data'}, 400
            user = User.get_by_id(user_id)
            if not user:
                return {'error': 'No user with specified id'}, 400
            for key, value in data.items():
                if key == 'password':
                    hash_ = get_hash(data["password"])
                    value = hash_
                setattr(user, key, value)
            db.session.commit()
            return {'msg': 'User updated', 'result': user_schema.dump(user)}, 200
        except IntegrityError:
            return {'error': 'Login or email already exist'}, 400


class LoginHistory(Resource):
    """API-view для просмотра истории входов."""

    @jwt_required()
    def get(self, user_id):
        """
        Get user login history
        Get user login history
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: uuid
            required: true
            default: all
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: User login history
            schema:
              properties:
                result:
                  type: array
                  items:
                    type: object
                  description: User login history
          400:
            description: Invalid uuid
        """
        if not is_uuid(user_id):
            return {'error': 'Invalid UUID format'}, 400
        history = Authentication.get_login_history(user_id)
        return {'result': [x.as_dict() for x in history]}, 200


class UserRoles(Resource):
    """API-view для просмотра ролей пользователя."""

    @jwt_required()
    def get(self, user_id):
        """
        Get users roles
        Get users roles
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: uuid
            required: true
            default: all
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: Users roles
            schema:
              properties:
                result:
                  type: array
                  items:
                    type: object
                  description: Users roles
          400:
            description: Invalid uuid
        """

        if not is_uuid(user_id):
            return {'error': 'Invalid UUID format'}, 400
        user = User.get_by_id(user_id)
        if not user:
            return {'error': 'No user with specified id'}, 400
        return {'result': [x.json() for x in user.roles]}, 200


class ChangeUserRoles(Resource):
    """API-view для изменения ролей пользователя."""

    @jwt_required()
    def post(self, user_id, role_id):
        """
        Add role to user
        Adds role <role_id> to user <user_id>
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: uuid
            required: true
            default: all
          - name: role_id
            in: path
            type: uuid
            required: true
            default: all
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: User role added
            schema:
              properties:
                msg:
                  type: string
                  description: Role added
          400:
            description: Invalid uuid format
        """

        if not (is_uuid(user_id) and is_uuid(role_id)):
            return {'error': 'Invalid UUID format'}, 400
        user = User.get_by_id(user_id)
        if not user:
            return {'error': 'No user with specified id'}, 400
        role = Role.find_by_id(role_id)
        if not role:
            return {'error': 'No role with specified id'}, 400
        user_datastore.add_role_to_user(user, role)
        db.session.commit()
        return {'msg': 'Success'}, 200

    @jwt_required()
    def delete(self, user_id, role_id):
        """
        Delete role from user
        Delete role <role_id> from user <user_id>
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: uuid
            required: true
            default: all
          - name: role_id
            in: path
            type: uuid
            required: true
            default: all
        security:
          BearerAuth:
            type: http
            scheme: bearer
        responses:
          200:
            description: User role deleted
            schema:
              properties:
                msg:
                  type: string
                  description: Role deleted
          400:
            description: Invalid uuid format
        """

        if not (is_uuid(user_id) and is_uuid(role_id)):
            return {'error': 'Invalid UUID format'}, 400
        user = User.get_by_id(user_id)
        if not user:
            return {'error': 'No user with specified id'}, 400
        role = Role.find_by_id(role_id)
        if not role:
            return {'error': 'No role with specified id'}, 400
        user_datastore.remove_role_from_user(user, role)
        db.session.commit()
        return {'msg': 'Success'}, 200