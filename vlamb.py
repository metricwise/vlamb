import functools
import hashlib
import http
import json
import logging
import os
import urllib.parse
import urllib.request

import boto3

_logger = logging.getLogger(__name__)

if os.environ['VTIGER_PASS'].startswith('/') or os.environ['VTIGER_PASS'].startswith('arn:'):
    os.environ['VTIGER_PASS'] = boto3.client('ssm').get_parameter(Name=os.environ['VTIGER_PASS'], WithDecryption=True)['Parameter']['Value']


# https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
def make_response(func):
    @functools.wraps(func)
    def wrapper(event, context):
        _logger.debug("request %s", event)
        try:
            message = func(event, context) or http.HTTPStatus.OK.phrase
            code = http.HTTPStatus.OK.value
        except VtapiError as e:
            _logger.error(e.message)
            message = e.message
            code = e.status
        except Exception as e:
            _logger.exception(str(e))
            message = http.HTTPStatus.INTERNAL_SERVER_ERROR.phrase
            code = http.HTTPStatus.INTERNAL_SERVER_ERROR.value
        response = {
            'body': json.dumps({'message': message}),
            'statusCode': code,
        }
        _logger.debug("response %s", response)
        return response
    return wrapper


def login():
    api = Vtapi(os.environ['VTIGER_HOST'])
    api.login(os.environ['VTIGER_USER'], os.environ['VTIGER_PASS'])
    return api


# https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_section.html
# https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_batch_item_failures_section.html
def wraps_sqs(func):
    @functools.wraps(func)
    def wrapper(event, context):
        with login() as vtapi:
            batch_item_failures = []
            for record in event['Records']:
                try:
                    func(record, context, vtapi)
                except Exception as e:
                    _logger.exception("%s", e)
                    batch_item_failures.append({'itemIdentifier': record['messageId']})
            response = {'batchItemFailures': batch_item_failures}
            _logger.debug("response %s", response)
            return response
    return wrapper


class Vtapi:
    def __init__(self, url):
        self.session_name = None
        self.url = url + '/webservice.php'

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        try:
            self.logout()
        finally:
            pass

    def count(self, module):
        query = f"select count(*) from {module};"
        result = self.query(query)
        return int(result[0]['count'])

    def create(self, module, values):
        data = {
            'operation': 'create',
            'sessionName': self.session_name,
            'elementType': module,
            'element': json.dumps(values),
        }
        with self._urlopen(self.url, data=data) as response:
            return self._result(response)

    def download(self, id):
        params = {
            'operation': 'download',
            'sessionName': self.session_name,
            'id': id,
        }
        with self._urlopen(self.url, params=params) as response:
            return self._result(response)

    def listtypes(self):
        params = {
            'operation': 'listtypes',
            'sessionName': self.session_name,
        }
        with self._urlopen(self.url, params=params) as response:
            return self._result(response)

    def login(self, username, accesskey):
        token = self._getchallenge(username)
        self._login(username, token, accesskey)

    def logout(self):
        if self.session_name:
            data = {
                'operation': 'logout',
                'sessionName': self.session_name,
            }
            self._urlopen(self.url, data=data)
            self.session_name = None
            self.user_id = None

    def query(self, query):
        params = {
            'operation': 'query',
            'sessionName': self.session_name,
            'query': query,
        }
        try:
            with self._urlopen(self.url, params=params) as response:
                return self._result(response)
        except:
            _logger.error("failed to query '%s'", query)
            raise

    def retrieve(self, module, limit=0, offset=0):
        query = f"select * from {module};"
        if limit or offset:
            query = query[:-1] + f" limit {offset}, {limit};"
        return self.query(query)

    def _getchallenge(self, username):
        params = {
            'operation': 'getchallenge',
            'username': username,
        }
        with self._urlopen(self.url, params=params) as response:
            result = self._result(response)
        token = result['token']
        return token

    def _login(self, username, token, accesskey):
        hasher = hashlib.md5()
        hasher.update(token.encode('utf-8'))
        hasher.update(accesskey.encode('utf-8'))
        data = {
            'operation': 'login',
            'username': username,
            'accessKey': hasher.hexdigest(),
        }
        with self._urlopen(self.url, data=data) as response:
            result = self._result(response)
        self.session_name, self.user_id = result['sessionName'], result['userId']

    def _result(self, response):
        body = json.loads(response.read().decode('utf-8'))
        if not body['success']:
            raise VtapiError(**body['error'], status=response.status)
        return body['result']

    def _urlopen(self, url, data=None, params=None):
        if params:
            url = url + '?' + urllib.parse.urlencode(params)
        if data:
            data = urllib.parse.urlencode(data).encode('utf-8')
        return urllib.request.urlopen(url, data=data)


class VtapiError(Exception):
    def __init__(self, code, message, status=None):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"{self.code}: {self.message}")
