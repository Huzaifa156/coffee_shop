import json
import os
from flask import request, _request_ctx_stack, abort
from functools import wraps
from jose import jwt
from urllib.request import urlopen
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('../../../.env')
load_dotenv(dotenv_path=dotenv_path)


AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
ALGORITHMS = ['RS256']
API_AUDIENCE = os.getenv('API_AUDIENCE')
# AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Auth Header

'''
@DONE implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
'''


def get_token_auth_header():

    if 'Authorization' not in request.headers:
        raise AuthError({'code': 'invalid_header',
                         'description': 'Authorization header need to be present'},
                        401)
    authorization = request.headers.get('Authorization')
    splitted_authorization_parts = authorization.split(' ')
    if len(splitted_authorization_parts) != 2:
        raise AuthError({'code': 'invalid_header',
                         'description': 'Authorization header need to be in Bearer token'},
                        401)
    if splitted_authorization_parts[0].lower() != 'bearer':
        raise AuthError(
            {
                'code': 'invalid_header',
                'description': 'Authorization header need to be to start with Bearer'},
            401)

    return splitted_authorization_parts[1]


'''
@DONE implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not in the payload permissions array
    return true otherwise
'''


def check_permissions(permission, payload):
    if 'permissions' not in payload:
        raise AuthError({'code': 'invalid_claims',
                        'description': 'Permissions not included in JWT.'
                         }, 400)

    if permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized',
            'description': 'Permission not found.'
        }, 403)
    return True


'''
@DONE implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here: https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
'''


def verify_decode_jwt(token):
    jsonUrl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonUrl.read())
    not_verify_header = jwt.get_unverified_header(token)
    if 'kid' not in not_verify_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization not well design'
        }, 401)

    generated_rsa = {}

    for key in jwks['keys']:
        if key['kid'] == not_verify_header['kid']:
            generated_rsa = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
            break

    if generated_rsa:
        try:
            payload = jwt.decode(
                token,
                generated_rsa,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer=f'https://{AUTH0_DOMAIN}/'
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthError({
                'code': 'token_expired',
                'description': 'Token expired'
            }, 401)
        except jwt.JWTClaimsError:
            raise AuthError({
                'code': 'invalid_claims',
                'description': 'check the audience and issuer.'
            }, 401)

        except Exception:
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to parse authentication token.'
            }, 400)


'''
@DONE implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and check the requested permission
    return the decorator which passes the decoded payload to the decorated method
'''


def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)

        return wrapper
    return requires_auth_decorator
