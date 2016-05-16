DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# minimum user age in days
USER_MINIMUM_AGE = 45


# Eve-related subs
REDDIT_EVE_SUBS = ['evedreddit',
                   'eve',
                   'evenewbies',
                   'eveporn',
                   'nullsecproblems',
                   'shitfits',
                   'dust514',
                   'evevalkyrie',
                   'evejobs',
                   'fittings',
                   'bravenewbies',
                   'evememes',
                   'subdreddit',
                   'fweddit',
                   'evemarketplace',
                   'everp',
                   'evetrading',
                   'evewormhole',
                   'killmailcrusaders',
                   'starcitizen_trades']

# Eve-related text to search for
REDDIT_SEARCH_TERMS = [
    'eve',
    'dreddit',
    'Test Alliance',
    'pleaseignore',
    'goons',
    'goonswarm',
    'goonfleet',
    'High Sec',
    'Low Sec',
    'Eve Uni',
    'EUni'
]

# APP Settings
####################################################################

# Max Reddit "Things" to limit requests to. 1000 is default max, 1500 with reddit gold.
MAX_OBJECTS_PER_CALL = 1000
# User Agent to present to reddit
USER_AGENT = "Ogree's Eve User Tools by /u/sammytrailor"

# Cache expiry in seconds
CACHE_EXPIRY = 86400  #1 day
CACHE_LOCATION = "c:/temp/"
