from flask import Flask, render_template, request, redirect, url_for, send_file, abort, send_from_directory
import sqlite3
import base64
from datetime import datetime, date
import yaml
import requests
from io import BytesIO
from queries import recent_detections, get_daily_summary, get_common_name, get_records_for_date_hour
from queries import get_records_for_scientific_name_and_date, get_earliest_detection_date
from queries import delete_detection, update_detection, get_all_identified_birds

app = Flask(__name__)
config = None
DBPATH = './data/speciesid.db'
NAMEDBPATH = './birdnames.db'


def format_datetime(value, format='%B %d, %Y %H:%M:%S'):
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')  # Adjusted input format to include microseconds
    return dt.strftime(format)


app.jinja_env.filters['datetime'] = format_datetime


@app.route('/')
def index():
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    earliest_date = get_earliest_detection_date()
    recent_records = recent_detections(5)
    daily_summary = get_daily_summary(today)
    identified_birds = get_all_identified_birds()
    return render_template('index.html', recent_detections=recent_records, daily_summary=daily_summary,
                           current_hour=today.hour, date=date_str, earliest_date=earliest_date, identified_birds=identified_birds)


@app.route('/frigate/<frigate_event>/thumbnail.jpg')
def frigate_thumbnail(frigate_event):
    frigate_url = config['frigate']['frigate_url']
    try:
        response = requests.get(f'{frigate_url}/api/events/{frigate_event}/thumbnail.jpg', stream=True)

        if response.status_code == 200:
            return send_file(response.raw, mimetype=response.headers['Content-Type'])
        else:
            # Return the single transparent pixel image from the local file if the actual image is not found
            return send_from_directory('static/images', '1x1.png', mimetype='image/png')
    except Exception as e:
        print(f"Error fetching image from frigate: {e}", flush=True)
        abort(500)


@app.route('/frigate/<frigate_event>/snapshot.jpg')
def frigate_snapshot(frigate_event):
    frigate_url = config['frigate']['frigate_url']
    try:
        # Fetch the image from frigate
        print("Getting snapshot from Frigate", flush=True)
        response = requests.get(f'{frigate_url}/api/events/{frigate_event}/snapshot.jpg', stream=True)

        if response.status_code == 200:
            # Serve the image to the client using Flask's send_file()
            return send_file(response.raw, mimetype=response.headers['Content-Type'])
        else:
            # Return the single transparent pixel image from the local file if the actual image is not found
            return send_from_directory('static/images', '1x1.png', mimetype='image/png')
    except Exception as e:
        # If there's any issue fetching the image, return a 500 error
        print(f"Error fetching image from frigate: {e}", flush=True)
        abort(500)


@app.route('/frigate/<frigate_event>/clip.mp4')
def frigate_clip(frigate_event):
    frigate_url = config['frigate']['frigate_url']
    try:
        # Fetch the clip from frigate
        print("Getting snapshot from Frigate", flush=True)
        response = requests.get(f'{frigate_url}/api/events/{frigate_event}/clip.mp4', stream=True)

        if response.status_code == 200:
            # Serve the image to the client using Flask's send_file()
            return send_file(response.raw, mimetype=response.headers['Content-Type'])
        else:
            # Return the single transparent pixel image from the local file if the actual image is not found
            return send_from_directory('static/images', '1x1.png', mimetype='image/png')
    except Exception as e:
        # If there's any issue fetching the image, return a 500 error
        print(f"Error fetching clip from frigate: {e}", flush=True)
        abort(500)


@app.route('/detections/by_hour/<date>/<int:hour>')
def show_detections_by_hour(date, hour):
    records = get_records_for_date_hour(date, hour)
    identified_birds = get_all_identified_birds()
    return render_template('detections_by_hour.html', date=date, hour=hour, records=records, identified_birds=identified_birds)


@app.route('/detections/by_scientific_name/<scientific_name>/<date>', defaults={'end_date': None})
@app.route('/detections/by_scientific_name/<scientific_name>/<date>/<end_date>')
def show_detections_by_scientific_name(scientific_name, date, end_date):
    if end_date is None:
        records = get_records_for_scientific_name_and_date(scientific_name, date)
        identified_birds = get_all_identified_birds()
        return render_template('detections_by_scientific_name.html', scientific_name=scientific_name, date=date,
                               end_date=end_date, common_name=get_common_name(scientific_name), records=records, identified_birds=identified_birds)


@app.route('/daily_summary/<date>')
def show_daily_summary(date):
    date_datetime = datetime.strptime(date, "%Y-%m-%d")
    daily_summary = get_daily_summary(date_datetime)
    today = datetime.now().strftime('%Y-%m-%d')
    earliest_date = get_earliest_detection_date()
    return render_template('daily_summary.html', daily_summary=daily_summary, date=date, today=today,
                           earliest_date=earliest_date)


@app.route('/delete_detection/<int:detection_id>', methods=['DELETE'])
def delete_detection_route(detection_id):
    try:
        delete_detection(detection_id)
        return '', 204
    except Exception as e:
        print(f"Error deleting detection: {e}", flush=True)
        return str(e), 500


@app.route('/update_detection/<int:detection_id>', methods=['POST'])
def update_detection_route(detection_id):
    try:
        new_display_name = request.form['new_display_name']
        update_detection(detection_id, new_display_name)
        return redirect(request.referrer)
    except Exception as e:
        print(f"Error updating detection: {e}", flush=True)
        return str(e), 500


def load_config():
    global config
    file_path = './config/config.yml'
    with open(file_path, 'r') as config_file:
        config = yaml.safe_load(config_file)


load_config()
