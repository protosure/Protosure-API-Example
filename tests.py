#!/usr/bin/env python
import json
import unittest
from jsonschema import validate

from app import app

SCHEMA = json.loads(open('jsonschema.json', 'r').read())


class ApiSchemaTestCase(unittest.TestCase):

    @staticmethod
    def create_event(uri, method, path, body='', content_type='application/json'):
        return {
            'requestContext': {
                'httpMethod': method,
                'resourcePath': uri,
            },
            'headers': {
                'Content-Type': content_type,
            },
            'pathParameters': path,
            'queryStringParameters': {},
            'body': body,
            'stageVariables': {},
        }

    @classmethod
    def get_app_response(cls, _app, uri, method, path='', **kwargs):
        response = _app(cls.create_event(uri, method, path, **kwargs), {})
        response['body'] = json.loads(response['body'])
        return response

    def _test_get_request(self):
        response = self.get_app_response(app, '/', 'GET', {})
        self.assertEqual(response['statusCode'], 200)
        validate(response['body'], SCHEMA)

    def test_post_response(self):
        response = self.get_app_response(app, '/', 'POST', body=json.dumps({
            'input_cm': 180,
            'input_kg': 90
        }))
        self.assertEqual(response['statusCode'], 200)
        validate(response['body'], SCHEMA)
        self.assertEqual(response['body']['calculation'],  {'output_BMI': 27.777777777777775})


if __name__ == '__main__':
    unittest.main()
