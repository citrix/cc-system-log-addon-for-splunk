# encoding = utf-8

import os
import sys
import time
import datetime

import json
import re


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    global_customer_id = helper.get_global_setting("customer_id")
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    
    start_date = helper.get_check_point("start_date")
    
    if start_date == None:
        opt_start_date = helper.get_arg('start_date')
        if opt_start_date != None and opt_start_date != "":
            regex = re.compile("^((?:[0-9]{2})?[0-9]{2})-((1[0-2]|0?[1-9])-(3[01]|[12][0-9]|0?[1-9]))$")
            if regex.match(opt_start_date):
                start_date = opt_start_date
            else:
                start_date = "2010-01-01"
        else:
            start_date = "2010-01-01"

    token = get_token(helper, global_customer_id, global_client_id, global_client_secret)

    get_new_records(helper, ew, global_customer_id, start_date, token)


def get_key_correct_case(keys, key):
    key_lower = key.lower()
    for currentKey in keys:
        if currentKey.lower() == key_lower:
            return currentKey
    
    return None


def get_token(helper, customer_id, client_id, client_secret):
    get_token_url = "https://trust.citrixworkspacesapi.net/{}/tokens/clients".format(customer_id)
    get_token_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    get_token_body = {
        "clientId": client_id,
        "clientSecret": client_secret
    }

    token_response = helper.send_http_request(get_token_url, "POST", parameters=None, payload=get_token_body,
                                        headers=get_token_headers, cookies=None, verify=True, cert=None,
                                        timeout=(10.0,60.0), use_proxy=False)

    token_response_status = token_response.status_code
    if token_response_status != 200:
        helper.log_error("Get token returned status code: {}".format(token_response_status))
        token_response.raise_for_status()

    get_token_json = token_response.json()
    token_key = get_key_correct_case(get_token_json.keys(), "token")
    token = get_token_json[token_key]
    
    return token


def get_new_records(helper, ew, customer_id, start_date, token):
    continuation_token = None
    current_start_date = start_date
    while True:
        get_records_url = "https://api-us.cloud.com/systemlog/records?StartDateTime={}".format(start_date)

        if continuation_token != None:
            get_records_url = "{}&ContinuationToken={}".format(get_records_url, continuation_token)

        get_records_auth = "CwsAuth Bearer={}".format(token)
        get_records_headers = {
            "Accept": "application/json",
            "Authorization": get_records_auth,
            "Citrix-CustomerId": customer_id
        }

        records_response = helper.send_http_request(get_records_url, "GET", parameters=None, payload=None,
                                            headers=get_records_headers, cookies=None, verify=True, cert=None,
                                            timeout=(10.0,60.0), use_proxy=False)

        records_response_status = records_response.status_code
        if records_response_status != 200:
            helper.log_error("Get records returned status code: {}".format(records_response_status))
            records_response.raise_for_status()

        get_records_json = records_response.json()

        items_key = get_key_correct_case(get_records_json.keys(), "items")
        for record in get_records_json[items_key]:
            records_event = helper.new_event(data=json.dumps(record), time=None, host=None,
                                            index=None, source=None, sourcetype=None, done=True,
                                            unbroken=True)
            ew.write_event(records_event)
            
            timestamp_key = get_key_correct_case(record.keys(), "utcTimestamp")
            utc_timestamp = record[timestamp_key]
            if current_start_date < utc_timestamp:
                current_start_date = utc_timestamp
                helper.save_check_point("start_date", current_start_date)

        continuation_token_key = get_key_correct_case(get_records_json.keys(), "continuationToken")
        continuation_token = get_records_json[continuation_token_key]
        
        if continuation_token == None:
            break


