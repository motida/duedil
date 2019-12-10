import uuid
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from time import time, sleep

import pandas as pd
from flask import Flask, jsonify, request, make_response

from match import match

# Constants
# TODO: move to config file
COMPANIES_FILE = '../../Desktop/duedil/companies.csv'
MAX_REQUESTS = 10
MAX_THREADS_IN_POOL = 3

# Load companies.csv to in memory list of dicts (assumes can be placed in memory).
df = pd.read_csv(COMPANIES_FILE, encoding='UTF-16')
companies = df.to_dict('records')

executor = ThreadPoolExecutor(MAX_THREADS_IN_POOL)
ongoing_requests = {}

app = Flask(__name__)


@app.route('/')
def alive():
    return 'Alive!'


@app.route('/submit', methods=['POST'])
def submit():
    """
    Endpoint for submitting a matching request
    Accepts file and optional threshold parameter
    :return: http json reply

    curl example:

        curl -X POST   'http://127.0.0.1:5000/submit?threshold=0.5' -F file=@sample_user_records.cs
    """
    # Check if server is not overloaded with requests
    # TODO: evict long outstanding requests.
    if len(ongoing_requests) >= MAX_REQUESTS:
        return jsonify({"received": "false", "error": "server overloaded, try again later"}, 429)

    try:
        file = request.files['file']
    except:
        return jsonify({"received": "false", "error": "No CSV file provided"}, 400)

    threshold_str = request.args.get('threshold', '0.0')  # Default threshold = 0.0
    try:
        threshold = min(max(float(threshold_str), 0.0), 1.0)
    except ValueError:
        return jsonify({"received": "false", "error": "threshold not a float (0.0 <= threshold <= 1.0)"}, 400)

    # convert csv file to pandas dataframe
    try:
        df = pd.read_csv(file)
    except Exception:
        return jsonify({"received": "false", "error": "file not in CSV form"}, 400)

    if 'name' not in df.columns:
        return jsonify({"received": "false", "error": "no name column in CSV form"}, 400)

    data = df.to_dict('records')
    jobid = uuid.uuid4().hex  # jobid for future reference

    future = executor.submit(process_request, jobid, data, threshold)
    ongoing_requests[jobid] = {'processed_rows': 0,
                               'total_rows': len(data),
                               'future': future,
                               'submitted': time(),
                               'result': data,
                               'orig_cols': list(df.columns.tolist())}

    return jsonify({"received": "true",
                    "received_at": ongoing_requests[jobid]['submitted'],
                    "threshold": threshold,
                    "jobid": jobid}, 201)


def process_request(jobid, data, threshold):
    """
    extends data with matching results from match algorithm.
    :param jobid: request identifier for tracking and returning results by later api calls.
    :param threshold: threshold for matching algorithm.
    :param data: companies to match as list of dictionaries.
    :return: None
    """
    for row in data:
        if 'name' in row:
            result = match(row['name'], companies, threshold)

            row.update({'matched_company': result['match_name'], 'matched_company_id': result['match_id']})
        ongoing_requests[jobid]['processed_rows'] += 1
        # sleep(1)


def get_status(jobid):
    """
    Find job status
    :param jobid: reference to job in system
    :return: (valid, done, response) - valid request? , done flag? and request output
    """
    output = None
    valid = False
    done = False

    if not jobid:
        return valid, done, jsonify({"status": 'no jobid provided', "jobid": jobid}, 400)
    if jobid in ongoing_requests:
        if ongoing_requests[jobid]['future'].done():
            output = jsonify({"status": 'done', "jobid": jobid}, 200)
            valid = True
            done = True
        else:
            output = jsonify({"status": 'running',
                              "progress": 'processed {} out of {}'.format(ongoing_requests[jobid]['processed_rows'],
                                                                          ongoing_requests[jobid]['total_rows']),
                              "jobid": jobid}, 200)
            valid = True
    else:
        output = jsonify({"status": 'jobid not found', "jobid": jobid}, 404)

    return valid, done, output


@app.route('/status', methods=['GET', 'POST'])
def status():
    """
    Get status for running job - done or running , if running how many rows processed so far
    :return: json response

    curl example:

        curl -X POST   'http://127.0.0.1:5000/status?jobid=XXXXXXXXXXXXXX'
    """
    jobid = request.args.get('jobid')
    valid, done, output = get_status(jobid)
    return output


@app.route('/pull', methods=['GET', 'POST'])
def pull():
    """
    Similiar to get status + return the updated csv file and removes jobid from jobs list
    :return: json response or output file

    curl example:

        curl -X POST   'http://127.0.0.1:5000/pull?jobid=XXXXXXXXXXXXXX'
    """
    jobid = request.args.get('jobid')
    valid, done, output = get_status(jobid)
    if done:
        df = pd.DataFrame(ongoing_requests[jobid]['result'], columns=ongoing_requests[jobid]['orig_cols'] +
                                                                     ['matched_company_id', 'match_name'])
        csv_file = StringIO()
        file_name = 'output.csv'
        df.to_csv(csv_file, encoding='utf-8', index=False)
        csv_output = csv_file.getvalue()
        csv_file.close()
        response = make_response(csv_output)
        response.headers["Content-Disposition"] = ("attachment; filename={}".format(file_name))
        response.headers["Content-Type"] = "text/csv"
        del ongoing_requests[jobid]
        return response
    else:
        return output


if __name__ == '__main__':
    app.run(debug=True)
