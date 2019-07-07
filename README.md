# Protosure API Example 

Built using Chalice 
https://github.com/aws/chalice

## To run
1. Set up AWS credentials
   https://github.com/aws/chalice#credentials
   
2. Deploy to AWS
   https://github.com/aws/chalice#deploying


## Rater API

API rater must accept two types of requests:

1. GET requests to the specified url e.g. `/` must return rater's fields list
2. POST request to the specified url e.g. `/` must return raters' fields list and calculated values

### Response format

Response must be valid against JSON Schema ([jsonschema.json](jsonschema.json))

It should be a JSON object with keys

 - `fields`
   contains all fields rater works with

   E.g.
   ```json
   [
    {
        "name": "input_cm",
        "label": "CM",
        "input": true,
        "output": false,
    }
   ]
   ```

   Properties:
     - `name`: **String**. Used to map between Protosure form data variables and API Rater variables
     - `label`: **String**. Human-readable label to use in configuration
     - `input`: **Boolean**. Marks field to be used as API Rater's input value - Protosure should send this field as calculation parameter
     - `output`: **Boolean**. Marks field to be used as API Rater's output value — API Rater must return this field as property in calculations


 - `calculations`
   contains object with calculated values

### Example

This repo contains simple [BMI](https://en.wikipedia.org/wiki/Body_mass_index) calculator
![](https://wikimedia.org/api/rest_v1/media/math/render/svg/a25f48e7bcb8270653f7b027e6dce80f0b6fcd90)

It accepts two values `input_cm` and `input_kg` and returns `output_BMI`.

>

1. Protosure sends a GET request to retrieve fields, must be used to send calculation parameters and get results

```bash
▲ ~ http https://3ae8wz88ni.execute-api.us-east-1.amazonaws.com/api/
HTTP/1.1 200 OK
Connection: keep-alive
Content-Length: 241
Content-Type: application/json
...

{
    "calculation": {},
    "fields": [
        {
            "input": true,
            "label": "CM",
            "name": "input_cm",
            "output": false
        },
        {
            "input": true,
            "label": "KG",
            "name": "input_kg",
            "output": false
        },
        {
            "input": false,
            "label": "BMI",
            "name": "output_BMI",
            "output": true
        }
    ]
}
```

2. When Protosure needs to get the calculation value it sends POST request and retrieves values from `calculation`
```bash
▲ ~ http POST https://3ae8wz88ni.execute-api.us-east-1.amazonaws.com/api/ input_kg=95 input_cm=180 -v
POST /api/ HTTP/1.1
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 37
Content-Type: application/json
Host: 3ae8wz88ni.execute-api.us-east-1.amazonaws.com
User-Agent: HTTPie/0.9.9

{
    "input_cm": "180",
    "input_kg": "95"
}

HTTP/1.1 200 OK
Connection: keep-alive
Content-Length: 273
Content-Type: application/json
Date: Thu, 18 Jan 2018 10:00:52 GMT
Via: 1.1 8ebc2b93de29d9744a950f4930f96579.cloudfront.net (CloudFront)
X-Amz-Cf-Id: XSQye5wVoyB7uVEdiNVCAfm8H_F2JKH7n1n9PTUH-EmhcNwnlTEf3g==
X-Amzn-Trace-Id: sampled=0;root=1-5a607054-0dc3979e519eafed2d3cbce1
X-Cache: Miss from cloudfront
x-amzn-RequestId: 77792191-fc36-11e7-af01-23d649cb85aa

{
    "calculation": {
        "output_BMI": 29.320987654320987
    },
    "fields": [
        {
            "input": true,
            "label": "CM",
            "name": "input_cm",
            "output": false
        },
        {
            "input": true,
            "label": "KG",
            "name": "input_kg",
            "output": false
        },
        {
            "input": false,
            "label": "BMI",
            "name": "output_BMI",
            "output": true
        }
    ]
}
```


### Tests

You can find test GET and POST requests examples in [tests.py](tests.py)

## Building a proxy to generate request for existing API

Same as before, but instead of doing calculation you generate request for the existing API,
send it, process response and return the data you need to Protosure in the response.
As an example you can check function `proxy_example` in [app.py](app.py)

![basic sequence diagram 2](https://user-images.githubusercontent.com/29029/46311228-c76d7700-c5c1-11e8-9f3e-c962ad6ad5f3.png)


## Custom data validation

Sometimes it's easier to write code that validates data rather than build rules using GUI.

It's possible with two tools:

1. Protosure webhooks to receive signal about the changes 
2. Prototsure API to get data for validation 

### Example

This repository contains an example of validation ZIP and Last Name + First Name value pairs as unique--a simple "clearance" system.
To check uniqueness we use the Protosure reports API with the MongoDB `aggregate` function.

We pass params (login, password and user email to notify) through the AWS lambda Environment

1. We write a webhook function `on_quote_submit` to accept a signal about submitted quote.
2. In the signal we extract ZIP and Last Name + First Name from quote
3. We validate unique ZIP using `check_zip` function. If it's not unique we send an email.
4. We validate unique Last Name + First Name using `check_name` function. If it's not unique we send an email.
5. Add webhook url to the settings
