import json
import os
from textwrap import dedent

import boto3
import requests
from botocore.exceptions import ClientError
from chalice import Chalice

app = Chalice(app_name='lambda_rater_api')
app.debug = True

if os.path.exists('deploy_env.json'):
    with open('deploy_env.json') as deploy_env_file:
        deploy_env: dict = json.loads(deploy_env_file.read())
        for key, value in deploy_env['Variables'].items():
            os.environ[key] = value


@app.route('/', methods=['GET', 'POST'], cors=True)
def api_get():
    request = app.current_request
    calculation = {
        'output_BMI': 0
    }
    if request.method == 'POST':
        input_cm = float(app.current_request.json_body.get('input_cm', 0) or 0)
        input_kg = float(app.current_request.json_body.get('input_kg', 0) or 0)
        if input_cm > 0 or input_kg > 0:
            calculation['output_BMI'] = input_kg / (pow(input_cm / 100, 2))

    return {
        'fields': [
            {'name': 'input_cm', 'label': 'CM', 'input': True, 'output': False, },
            {'name': 'input_kg', 'label': 'KG', 'input': True, 'output': False, },
            {'name': 'output_BMI', 'label': 'BMI', 'input': False, 'output': True, },
        ],
        'calculation': calculation,
    }


@app.route('/proxy_example', methods=['GET', 'POST'], cors=True)
def proxy_example():
    request = app.current_request
    calculation = {}
    if request.method == 'POST':
        input_cm = float(app.current_request.json_body.get('input_cm', 0) or 0)
        input_kg = float(app.current_request.json_body.get('input_kg', 0) or 0)
        main_api_request = {
            'nested_object': {
                'another_nested_object': {
                    'meters': int(input_cm) / 100,
                    'grams': int(input_kg) * 1000
                }
            },
        }
        main_api_response = requests.post('https://api.enterprise.mainframe.com', json=main_api_request)
        assert main_api_response.status_code == 200

        # Assume response has schema
        # {
        #    "human": {
        #       "on_earth": {
        #           "BMI": 12.34
        #       }
        #    }
        # }

        bmi = main_api_response.json()['human']['on_earth']['BMI']
        calculation = {
            'output_BMI': bmi
        }

    rater_data = {
        'fields': [
            {'name': 'input_cm', 'label': 'CM', 'input': True, 'output': False, },
            {'name': 'input_kg', 'label': 'KG', 'input': True, 'output': False, },
            {'name': 'output_BMI', 'label': 'BMI', 'input': False, 'output': True, },
        ],
        'calculation': calculation,
    }
    return rater_data


@app.route('/hey', methods=['GET'], cors=True)
def test():
    return list(os.environ)


HOST = os.environ.get('QUOTE_SUBMIT_HANDLER_PROTOSURE_HOST')
WIDGET_ADDRESS_ID = os.environ.get('QUOTE_SUBMIT_HANDLER_WIDGET_ADDRESS_ID')
FIRST_NAME_ID = os.environ.get('QUOTE_SUBMIT_HANDLER_WIDGET_FIRST_NAME_ID')
LAST_NAME_ID = os.environ.get('QUOTE_SUBMIT_HANDLER_WIDGET_LAST_NAME_ID')
EMAIL = os.environ.get('QUOTE_SUBMIT_HANDLER_PROTOSURE_EMAIL')
PASSWORD = os.environ.get('QUOTE_SUBMIT_HANDLER_PROTOSURE_PASSWORD')
ALERT_EMAIL = os.environ.get('QUOTE_SUBMIT_HANDLER_ALERT_EMAIL')


@app.route('/on_quote_submit', methods=['POST'], cors=True)
def on_quote_submit():
    session = requests.Session()

    login_url = f'{HOST}/auth/ajax_login/'
    r = session.post(login_url, json={
        'email': EMAIL,
        'password': PASSWORD
    })
    if r.status_code != 200:
        message = dedent(f"""
        Login error
        Status code: {r.status_code}
        Content: \n{r.content}
        """)
        raise Exception(message)

    quote = app.current_request.json_body['quote']

    check_zip(session, quote)
    check_name(session, quote)


def check_zip(session, quote):
    address = quote['formData'].get(WIDGET_ADDRESS_ID, None)
    assert address, f"Address widget with id {WIDGET_ADDRESS_ID} not found"
    zip_ = address.get('zip', '')
    ZIP_QUERY = {
        "aggregate": [
            {"$match": {f"formData.{WIDGET_ADDRESS_ID}.zip": zip_}},
            {"$count": "count"}
        ]
    }
    response = session.post(f'{HOST}/api/reports/query/', json=ZIP_QUERY)

    if response.status_code != 200:
        message = dedent(f"""
        ZIP Query error
        Status code: {response.status_code}
        Content: \n{response.content}
        """)
        raise Exception(message)

    count = response.json()[0]['count']
    if count > 1:
        text = dedent(f"""
            New quote was submitted with ZIP "{zip_}".
            Total quotes with ZIP "{zip_}" is {count}.
        """)
        print(text)
        send_email(ALERT_EMAIL, 'Protosure Alert', text)


def check_name(session, quote):
    first_name = quote['formData'][FIRST_NAME_ID]
    last_name = quote['formData'][LAST_NAME_ID]
    NAME_QUERY = {
        "aggregate": [
            {
                "$match": {
                    "$and": [
                        {f"formData.{FIRST_NAME_ID}": first_name},
                        {f"formData.{LAST_NAME_ID}": last_name},
                    ]
                }
            },
            {"$count": "count"}
        ]
    }
    response = session.post(f'{HOST}/api/reports/query/', json=NAME_QUERY)
    count = response.json()[0]['count']
    if count > 1:
        text = dedent(f"""
            New quote was submitted with  first name "{first_name}" and last name "{last_name}".
            Total quotes with  first name "{first_name}" and last name "{last_name}" is {count}.
        """)
        print(text)
        send_email(os.environ.get('ALERT_EMAIL'), 'Protosure Alert', text)


def send_email(to, header, body):
    client = boto3.client('ses', region_name="us-east-1")
    try:
        response = client.send_email(
            Destination={'ToAddresses': [to], },
            Message={
                'Body': {'Text': {'Charset': "UTF-8", 'Data': body}},
                'Subject': {'Charset': "UTF-8", 'Data': header},
            },
            Source="Protosure Bot <bot@api-demo.protosure.io>",
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
