from flask import Flask, render_template, jsonify, send_from_directory
import requests
from RedditOAuth import reddit
from Decorators import crossdomain
import datetime
import pickle
import re
import os

app = Flask(__name__, static_url_path='', instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py', silent=True)


@app.route("/")
@app.route("/user")
@app.route("/user-force")
def hello_world():
    return render_template("index.html")


@app.route("/__authcb")
def oauth_auth_callback():
    return "Done"


@app.route("/get_auth_url")
def get_auth_url():
    return "AuthURL"

@app.route("/user/<username>/")
@app.route("/user/<username>")
def get_user(username=None):
    return render_template("index.html", username=username, force=False, error=None)


@app.route("/user-force/<username>")
def force_user(username=None):
    return render_template("index.html", username=username, force=True, error=None)


# JSON Pages
@app.route("/getuserdetails/<username>")
@crossdomain(origin='*')
def get_user_details(username=None):
    return retrieve_user_details(username, False)


@app.route("/forceuserdetails/<username>")
@crossdomain(origin='*')
def force_user_details(username=None):
    return retrieve_user_details(username, True)


@app.route("/authenticate")
@crossdomain(origin='*')
def is_authenticated():
    return jsonify({'authenticated': True})


# Error Pages
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error="404"), 404


# PROCESSING FUNCTIONS
def retrieve_user_details(username, force):
    user_data = {}

    response = {
        'error': 0,
        'errorMsg': "",
        'user_data': user_data
    }
    try:

        if force:
            user_data = get_user_details_from_reddit(username)

            response['cached'] = False  # user_data['cached']
            response['query_time'] = datetime.datetime.utcnow().strftime(app.config['DATE_FORMAT'])
            response['user_data'] = user_data

        else:
            # Attempt to find our data in the cache
            if cache_file_exists(username):
                user_data = get_user_details_from_cache(username)

                response['cached'] = user_data['cached']
                response['query_time'] = user_data['query_time']
                response['user_data'] = user_data
            else:
                user_data = get_user_details_from_reddit(username)

                response['cached'] = False
                response['query_time'] = datetime.datetime.utcnow().strftime(app.config['DATE_FORMAT'])
                response['user_data'] = user_data

    except ValueError as value_error:
        response['error'] = 1
        response['errorMsg'] = value_error.message
    except IOError as io_error:
        response['error'] = 1
        response['errorMsg'] = "Error reading from disk"
        print io_error.message
    except requests.ConnectionError:
        response['error'] = 1
        response['errorMsg'] = "Could not connect to Reddit. Is Reddit down?"
    except requests.HTTPError:
        response['error'] = 1
        response['errorMsg'] = "Error retrieving information from Reddit: Bad Request or Response (API issue)"
    except Exception as ex:
        response['error'] = 1
        response['errorMsg'] = "An unknown error has occurred"
        print ex.message

    return jsonify(**response)


def get_user_details_from_reddit(username):
    user_details = {'query_time': datetime.datetime.utcnow(), 'details': {}}
    trophies = {}
    try:

        client_id = app.config['REDDIT_CLIENT_ID']
        client_secret = app.config['REDDIT_SECRET_KEY']
        refresh_token = app.config['REDDIT_REFRESH_TOKEN']
        user_agent = app.config['USER_AGENT']
    except:
        raise AttributeError('Application Configuration incorrect or not specified')

    r = reddit.Reddit(client_id, client_secret, refresh_token, user_agent)

    # Get our details from Reddit

    about_data = r.get_user_details(username)
    if len(about_data) <= 0:
        raise ValueError("Username not found")

    overview_data = r.get_user_overview(username)
    trophy_data = r.get_user_trophies(username)

    # crunch the reddit data and format it for display
    user_details = process_about_user(about_data, user_details)
    user_details = process_overview(overview_data, user_details)
    trophies = process_trophies(trophy_data)

    user_details['trophies'] = trophies
    user_details['query_time'] = datetime.datetime.utcnow().strftime(app.config['DATE_FORMAT'])
    user_details['cached'] = False

    # cache our content
    save_user_data(user_details)

    return user_details


def get_user_details_from_cache(username):
    user_details = {}

    try:
        user_details = load_user_data_from_file(username)
    except:
        user_details = get_user_details_from_reddit(username)

    return user_details


def convert_utc_to_month_and_year(utc_timestamp):
    created_date = datetime.datetime.utcfromtimestamp(utc_timestamp)
    return created_date.strftime("%m/%Y")


def process_trophies(trophy_list):
    output = {}

    for trophy in trophy_list:
        if trophy['kind'] == 't6':  # t6 is the ThingCode for a Trophy
            output[trophy['data']['name']] = {'description': trophy['data']['description'],
                                              'icon': trophy['data']['icon_40']}

    return output


def process_about_user(about_data, user_data):
    output = user_data
    if about_data['kind'] != "t2":
        # we haven't found a user.
        raise ValueError("Redditor not found")

    minimum_age_seconds = 86400 * app.config['USER_MINIMUM_AGE']
    creation_date = datetime.datetime.utcfromtimestamp(about_data['data']['created_utc'])
    creation_date_ok = (datetime.datetime.utcnow() - creation_date).total_seconds() > minimum_age_seconds

    output['username'] = about_data['data']['name']
    output['created'] = creation_date.strftime(app.config['DATE_FORMAT'])  # TODO: Make Date Format Configurable
    output['creationDateOK'] = creation_date_ok
    output['isGold'] = about_data['data']['is_gold']
    output['isMod'] = about_data['data']['is_mod']
    output['isSuspended'] = False  # about_data['data']['is_suspended']
    output['isEmployee'] = False  # about_data['data']['is_employee']

    return output


def process_overview(overview_data, user_data):
    output = user_data
    details = user_data['details']
    oldest_eve_content = datetime.datetime.utcnow()
    has_eve_content = False

    eve_content = {}

    # reset our output overivew
    # TODO: WIll need to update this section if combining multiple reddit usernames
    output['totalComments'] = 0
    output['totalSubmissions'] = 0
    output['commentKarma'] = 0
    output['submissionKarma'] = 0
    output['firstEvePost'] = ""
    output['details'] = {}

    if 'eve_content' not in output.keys():
        output['eve_content'] = eve_content
    else:
        eve_content = output['eve-content']


    for thing in overview_data:

        month = datetime.datetime.utcfromtimestamp(thing['data']['created_utc']).strftime("%m/%Y")

        # Comment
        if thing['kind'] == 't1':
            output['totalComments'] += 1
            output['commentKarma'] += thing['data']['score']

            # update our monthly stats
            if month not in output['details'].keys():
                output['details'][month] = {
                    'totalSubmissions': 0,
                    'totalComments': 1,
                    'totalCommentKarma': thing['data']['score'],
                    'totalSubmissionKarma': 0,
                    'subreddits': {}
                }
            else:
                output['details'][month]['totalComments'] += 1
                output['details'][month]['totalCommentKarma'] += thing['data']['score']

            # update our subreddit stats for this month
            if thing['data']['subreddit'] not in output['details'][month]['subreddits'].keys():
                output['details'][month]['subreddits'][thing['data']['subreddit']] = {
                    'totalSubmissions': 0,
                    'totalComments': 1,
                    'totalCommentKarma': thing['data']['score'],
                    'totalSubmissionKarma': 0,
                }
            else:
                output['details'][month]['subreddits'][thing['data']['subreddit']]['totalComments'] += 1
                output['details'][month]['subreddits'][thing['data']['subreddit']]['totalCommentKarma'] += \
                thing['data']['score']

            if is_eve_subreddit(thing['data']['subreddit']) or contains_eve_content(thing['data']['body']):
                has_eve_content = True
                if oldest_eve_content > datetime.datetime.utcfromtimestamp(thing['data']['created_utc']):
                    oldest_eve_content = datetime.datetime.utcfromtimestamp(thing['data']['created_utc'])

                eve_content[thing['data']['name']] = {
                    'created':  datetime.datetime.utcfromtimestamp(thing['data']['created_utc']).strftime(app.config['DATE_FORMAT']),
                    'subreddit': thing['data']['subreddit'],
                    'link_title': thing['data']['link_title'],
                    'link_author': thing['data']['link_author'],
                    'parent': thing['data']['parent_id'],
                    'score': thing['data']['score'],
                    'url': thing['data']['link_url'],
                    'body': thing['data']['body'],
                    'is_submission': False
                }
                # TODO: Update First Eve Post

        # Link/Submission
        if thing['kind'] == 't3':
            output['totalSubmissions'] += 1
            output['submissionKarma'] += thing['data']['score']

            # update our monthly stats
            if month not in output['details'].keys():
                output['details'][month] = {
                    'totalSubmissions': 0,
                    'totalComments': 1,
                    'totalCommentKarma': thing['data']['score'],
                    'totalSubmissionKarma': 0,
                    'subreddits': {}
                }
            else:
                output['details'][month]['totalComments'] += 1
                output['details'][month]['totalCommentKarma'] += thing['data']['score']

            # update our subreddit stats for this month
            if thing['data']['subreddit'] not in output['details'][month]['subreddits'].keys():
                output['details'][month]['subreddits'] = {
                    'totalSubmissions': 1,
                    'totalComments': 0,
                    'totalCommentKarma': 0,
                    'totalSubmissionKarma': thing['data']['score'],
                }
            else:
                output['details'][month]['subreddits'][thing['data']['subreddit']]['totalSubmissions'] += 1
                output['details'][month]['subreddits'][thing['data']['subreddit']]['totalSubmissionKarma'] += \
                    thing['data']['score']

            if is_eve_subreddit(thing['data']['subreddit']) or contains_eve_content(thing['data']['selftext']):
                has_eve_content = True
                if oldest_eve_content > datetime.datetime.utcfromtimestamp(thing['data']['created_utc']):
                    oldest_eve_content = datetime.datetime.utcfromtimestamp(thing['data']['created_utc'])

                eve_content[thing['data']['name']] = {
                    'created':  datetime.datetime.utcfromtimestamp(thing['data']['created_utc']).strftime(app.config['DATE_FORMAT']),
                    'subreddit': thing['data']['subreddit'],
                    'link_title': thing['data']['title'],
                    'link_author': thing['data']['author'],
                    'parent': "",
                    'score': thing['data']['score'],
                    'url': thing['data']['url'],
                    'body': thing['data']['selftext'],
                    'is_submission': True
                }
                # TODO: Update First Eve Post

    # output['details'] = details
    output['hasEveContent'] = has_eve_content
    output['firstEvePost'] = oldest_eve_content.strftime(app.config['DATE_FORMAT'])

    output['eve_content'] = eve_content
    return output


def contains_eve_content(text):
    try:
        for phrase in app.config['REDDIT_SEARCH_TERMS']:
            if find_whole_word(phrase)(text.lower()):
                return True

        return False
    except Exception:
        return False


def is_eve_subreddit(subreddit):
    try:
        is_eve = subreddit.lower() in app.config['REDDIT_EVE_SUBS']
    except:
        raise AttributeError('Application Configuration incorrect or not specified')

    return is_eve


def find_whole_word(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def save_user_data(user_data):
    username = user_data['username']
    user_data['cached'] = True
    user_data['query_time'] = datetime.datetime.utcnow().strftime(app.config['DATE_FORMAT'])

    with open("{0}{1}.dat".format(app.config['CACHE_LOCATION'], username), 'wb+' ) as output:
        pickle.dump(user_data, output, -1)
    return ""


def cache_file_exists(username):
    if 'CACHE_LOCATION' in app.config.keys():
        return os.path.isfile("{0}{1}.dat".format(app.config['CACHE_LOCATION'], username))
    else:
        raise AttributeError('Application Configuration incorrect or not specified')


def load_user_data_from_file(username):
    try:
        with open("{0}{1}.dat".format(app.config['CACHE_LOCATION'], username), 'rb') as input:
            user_data = pickle.load(input)
        #
            return user_data
    except:
        return None


if __name__ == '__main__':
    app.run()
