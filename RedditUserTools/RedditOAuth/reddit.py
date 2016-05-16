import requests
import requests.auth
import datetime
import time


class Reddit:
    # Token Information
    refresh_token = ""
    access_token = ""
    access_expiry = datetime.datetime.utcnow()
    access_scopes = {}

    # App Information
    client_id = ""
    client_secret = ""
    user_agent = ""

    # Rate limit information
    rate_limit_remaining = 0  # number of requests remaining in this 10min block
    rate_limit_used = 0  # number of requests used so far in the 10min block
    rate_limit_reset = 0  # number of seconds remaining until rate limit resets (approximate)

    # If we have less than throttle_limit requests/sec remaining, sleep for throttle_time
    throttle_limit = 0.5
    throttle_time = 1

    def __init__(self, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, USER_AGENT):
        self.refresh_token = REFRESH_TOKEN
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.user_agent = USER_AGENT

        return

    def generate_auth_URL(self):
        return

    def authenticate(self):

        return self.refresh_access_token()

    def refresh_access_token(self):
        url = "https://www.reddit.com/api/v1/access_token"
        headers = self._get_basic_headers()
        post_data = {"grant_type": "refresh_token",
                     "refresh_token": self.refresh_token
                     }
        client_auth = self._get_authentication()

        response = requests.post(url, auth=client_auth, headers=headers, data=post_data)

        # check if a good response
        token_json = response.json()

        self.access_token = token_json['access_token']
        self.access_expiry = datetime.datetime.utcnow() + datetime.timedelta(0, token_json[
            'expires_in'])  # now + number of seconds reddit says it will expire - could reduce this for a fudge factor
        self.access_scopes = token_json['scope'].split(" ")

    def get_reddit_results(self, url, params):

        if datetime.datetime.utcnow() > self.access_expiry:
            self.refresh_access_token()

        headers = self._get_basic_headers()
        headers.update({"Authorization": "bearer " + self.access_token})

        if self.rate_limit_reset > 0 and (self.rate_limit_remaining / self.rate_limit_reset < self.throttle_limit):
            # print "THROTTLING!"
            time.sleep(self.throttle_time)

        response = requests.get(url, params=params, headers=headers)

        # Update our rate limits
        if "X-RateLimit-Used" in response.headers:
            self.rate_limit_remaining = float(response.headers['X-RateLimit-Remaining'])
            self.rate_limit_used = int(response.headers['X-RateLimit-Used'])
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])

        results_json = ""
        if response.status_code == requests.codes.ok:
            results_json = response.json()

        return results_json

    def get_user_details(self, username):
        # TODO: Handle Redditor Not Found
        url = "https://oauth.reddit.com/user/{0}/about/.json".format(username)

        return self.get_reddit_results(url=url, params={})

    def get_user_overview(self, username, limit=0):
        url = "https://oauth.reddit.com/user/{0}/overview/.json".format(username)
        total_things = 0

        params = {'limit': 1000}  # TODO: Make Overview Request Limit adjustable?

        overview_data = self.get_reddit_results(url=url, params=params)

        # Getting overview should return a Listing, if not, probably an error
        if overview_data['kind'] != "Listing":
            # we have no data returned or an error
            return None

        # We want to all the 'things'
        output = overview_data['data']['children']
        total_things = len(output)

        # reddit listings will contain a value for 'after' if there is more to add
        # TODO: Limiting amount of things is crude - could go over limit
        while overview_data['data']['after'] and (limit <= 0 or total_things < limit):
            # keep getting more
            params['after'] = overview_data['data']['after']

            overview_data = self.get_reddit_results(url=url, params=params)

            if overview_data['kind'] == "Listing":
                output += overview_data['data']['children']
                total_things = len(output)

        return output

    def get_user_trophies(self, username):
        url = "https://oauth.reddit.com/api/v1/user/{0}/trophies".format(username)
        params = {}

        trophy_data = self.get_reddit_results(url=url, params=params)

        if trophy_data['kind'] != "TrophyList":
            return {}
            # something went wrong
        return trophy_data['data']['trophies']

    def _get_basic_headers(self):
        return {"User-agent": self.user_agent}

    def _get_authentication(self):
        return requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
