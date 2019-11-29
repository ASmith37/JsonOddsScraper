# -*- coding: utf-8 -*-
"""
Created on Sun Oct 29 22:06:16 2017

@author: The Man
"""

import requests
from json import loads, dumps
from yaml import load as yaml_load
import os
import sqlite3
import time

debug_hold = None

credentials = ['', '']
pinn_path = 'https://api.pinnacle.com/'
DB_name = 'V2_Odds_2.db'
schema_name = 'PinnacleSchema_v3.sql'

if os.name == 'nt':
    source_path = 'C:\\Users\\The Man\\Documents\\PythonStuff\\PinnacleV2\\'
elif os.name == 'posix':
    source_path = '/home/pi/PythonStuff/PinnacleV2/' # need to check this

with open(source_path + 'auth.yaml', 'r') as f:
    hold = yaml_load(f.read())
    credentials = (hold['username'], hold['password'])
    RUN_MODE = hold['run_env']
# print credentials

DB_IS_NEW = not os.path.exists(source_path + DB_name)
conn = sqlite3.connect(source_path + DB_name)
conn.executescript("PRAGMA foreign_keys = ON;") # Make foreign keys work

with open (source_path + schema_name, 'r') as f:
    DB_schema = f.read()

if DB_IS_NEW:
    print "Can't find DB. Need to execute schema."
    conn.executescript(DB_schema)
else:
    print "Successfully opened DB " + DB_name
c = conn.cursor()
'''
==========================================================
   Functions to handle getting data out of the database
==========================================================
'''

'''
==========================================================
      Functions to handle getting data from Pinnacle
==========================================================
'''

def is_valid_league(league_id):
    '''
    Takes in a league (int) or list of leagues [(int)]
    and says whether all of them are in the DB as scrapeable
    '''
    print "Checking is league is valid:", league_id
    query = '''SELECT league_id FROM league WHERE scrape = 1'''
    c.execute(query)
    valid_leagues = [x[0] for x in c.fetchall()]
    if isinstance(league_id, int):
        # print "league_id is int"
        return league_id in valid_leagues
    elif isinstance(league_id, list):
        # print "league_id is list"
        if len(league_id) == 0:
            return False
        return all(x in valid_leagues for x in league_id)
    else:
        return False

def get_sports():
    r = requests.get(pinn_path + 'v2/sports', auth = credentials)
    assert r.status_code == 200
    result = loads(r.content)['sports']
    return result

def get_leagues(sport_id):
    print "Getting leagues for sport", sport_id
    assert isinstance(sport_id, int)
    assert sport_id > 0 and sport_id < 40
    query_url = make_url(sport_id, 'leagues')
    r = requests.get(query_url, auth = credentials)
    # print r.content
    result = loads(r.content)['leagues']
    return result

def get_fixtures(sport_id):
    assert isinstance(sport_id, int)
    '''
    Newer, sport-based version
    to replace league-based version
    '''
    last_update = get_last_update(sport_id, 'fixtures')
    print "Get fixtures for sport", sport_id
    assert isinstance(last_update, int) or last_update == None
    query_url = make_url(sport_id, 'fixtures', last_update)
    print query_url
    r = requests.get(query_url, auth = credentials)
    print "Response:", type(r.content), len(r.content)
    assert r.status_code == 200
    if r.content in ["", "{}"]:
        result = {'league': [], 'sportId': sport_id}
    else:
        result = loads(r.content)
    result['ostime'] = time.time()
    if last_update == None:
        result['next_update'] = result['ostime'] + 60
    else:
        result['next_update'] = result['ostime'] + 5
    return result

def get_settled_fixtures(sport_id):
    assert isinstance(sport_id, int)
    '''
    This is the new, sport-based version
    '''
    print "Get settled fixtures for sport", sport_id
    last_update = get_last_update(sport_id, 'settled')
    assert isinstance(last_update, int) or last_update == None
    query_url = make_url(sport_id, 'settled', last_update)
    print query_url
    r = requests.get(query_url, auth = credentials)
    print "Response:", type(r.content), len(r.content)
    assert r.status_code == 200
    if r.content in ["", "{}"]:
        result = {'leagues': [], 'sportId': sport_id}
    else:
        result = loads(r.content)
    result['ostime'] = time.time()
    if last_update == None:
        result['next_update'] = result['ostime'] + 60
    else:
        result['next_update'] = result['ostime'] + 5
    return result

def get_odds(sport_id):
    '''
    Returns the data from scraping.
    '''
    last_update = get_last_update(sport_id, 'odds')
    query_url = make_url(sport_id, 'odds', last_update)
    print "Query url:", query_url
    r = requests.get(query_url, auth = credentials)
    print "Response:", type(r.content), len(r.content)
    #print type(r.content)
    #print len(r.content)
    #print r.content
    #print "End of response data"
    assert r.status_code == 200
    if r.content in ["", "{}"]:
        result = {'leagues': [], 'sportId': sport_id}
    else:
        result = loads(r.content)
    result['ostime'] = time.time()
    if last_update == None:
        result['next_update'] = result['ostime'] + 60
    else:
        result['next_update'] = result['ostime'] + 5
    # set_last_update(league_id, 'odds', result['last'])
    return result

# a1 = get_odds_3(22)
# print a1
'''
==========================================================
Functions to handle logging data from Pinnacle into the DB
==========================================================
'''

def log_fixtures(payload):
    conn.commit() # To make sure there are no staged changes
    for league in payload['league']:
        print "Logging fixtures for league", league['id']
        for event in league['events']:
            print "Logging fixtures for event", event['id']
            update_query = u'''-- Try to update
                           UPDATE event
                           SET start_time = "{2}", betting_status = "{3}"
                           WHERE event_id = {1};'''.format(
                           league['id'], event['id'], event['starts'], event['status'])
            insert_query = u'''-- If no update happened
                           INSERT INTO event
                           (sport_id, league_id, event_id, start_time, betting_status, home_name, away_name)
                           SELECT ?, ?, ?, ?, ?, ?, ?
                           WHERE (Select Changes() = 0);'''
            insert_data = (payload['sportId'], league['id'], event['id'],
                           event['starts'], event['status'], event['home'],
                           event['away'])
            # print update_query
            c.execute(update_query)
            # print insert_query
            c.execute(insert_query, insert_data)
            conn.commit() # Has to be per-event because of Select Changes query
    if 'last' in payload:
        set_last_update(payload['sportId'], 'fixtures', payload['last'])
        # set_next_update(payload['sport'], 'fixtures', payload['next_update'])

def log_settled_fixtures(payload):
    for league in payload['leagues']:
        print "Logging settled fixtures for league", league['id']
        for event in league['events']:
            print "Logging settled fixtures for event", event['id']
            for period in event['periods']:
                cancel_reason = "null"
                if 'cancellationReason' in period:
                    cancel_reason = str(period['cancellationReason'])
                sql_query = u''' -- update fixture if present
                            UPDATE period
                            SET settled_status = {2},
                                settled_id = {3},
                                settled_time = "{4}",
                                team_1_score = {5},
                                team_2_score = {6},
                                cancellation_details = "{7}"
                            WHERE
                                event_id = {0} AND
                                match_period = {1};'''.format(
                            event['id'],
                            period['number'],
                            period['status'],
                            period['settlementId'],
                            period['settledAt'],
                            period['team1Score'],
                            period['team2Score'],
                            cancel_reason)
                c.execute(sql_query)
        conn.commit()
    if 'last' in payload:
        set_last_update(payload['sportId'], 'settled', payload['last'])
        #set_last_update(league['id'], 'settled', payload['last'])

def log_odds(payload):
    for league in payload['leagues']:
        print "Logging odds for league", league['id']
        for event in league['events']:
            print "Logging odds for event", event['id']
            for period in event['periods']:
                update_query = u'''-- Try to update
                               UPDATE period
                               SET cutoff_time = "{2}"
                               WHERE event_id = {0} AND
                                     match_period = {1};'''.format(
                               event['id'], period['number'], period['cutoff'])
                insert_query = u'''--if no update happened
                               INSERT INTO period
                               (sport_id, league_id, event_id, match_period, cutoff_time)
                               SELECT {0}, {1}, {2}, {3}, "{4}"
                               WHERE (Select Changes() = 0);'''.format(
                               payload['sportId'], league['id'], event['id'], period['number'], period['cutoff'])
                # print update_query
                c.execute(update_query)
                # print insert_query
                c.execute(insert_query)
                conn.commit()
                if 'moneyline' in period:
                    if 'draw' in period['moneyline']:
                        draw_price = period['moneyline']['draw']
                    else:
                        draw_price = "null"
                    line_id = period['lineId']
                    sql_query = u'''-- adding a new odds entry
                                INSERT INTO odds_moneyline
                                (sport_id, league_id, event_id, match_period,
                                line_id, time_stamp, cutoff_time,
                                max_bet,
                                home_price, away_price, draw_price)
                                VALUES
                                ({0}, {1}, {2}, {3},
                                {4}, {5}, "{6}",
                                {7},
                                {8}, {9}, {10});
                                '''.format(
                                payload['sportId'], league['id'], event['id'], period['number'],
                                line_id, payload['ostime'], period['cutoff'],
                                period['maxMoneyline'],
                                period['moneyline']['home'],
                                period['moneyline']['away'],
                                draw_price)
                    # print sql_query
                    c.execute(sql_query)
                    conn.commit()
                if 'totals' in period:
                    for total in period['totals']:
                        line_id = period['lineId']
                        if 'altLineId' in total:
                            line_id = total['altLineId']
                        sql_query = u'''-- adding a new total entry
                                    INSERT INTO odds_total
                                    (sport_id, league_id, event_id, match_period,
                                    line_id, time_stamp, cutoff_time,
                                    max_bet,
                                    points, over_price, under_price)
                                    VALUES
                                    ({0}, {1}, {2}, {3},
                                    {4}, {5}, "{6}",
                                    {7},
                                    {8}, {9}, {10});
                                    '''.format(
                                    payload['sportId'], league['id'], event['id'], period['number'],
                                    line_id, payload['ostime'], period['cutoff'],
                                    period['maxTotal'],
                                    total['points'], total['over'], total['under'])
                        c.execute(sql_query)
                        conn.commit()
                if 'spreads' in period:
                    for spread in period['spreads']:
                        line_id = period['lineId']
                        if 'altLineId' in spread:
                            line_id = spread['altLineId']
                        sql_query = u''' -- new entry
                                    INSERT INTO odds_spread
                                    (sport_id, league_id, event_id, match_period,
                                    line_id, time_stamp, cutoff_time,
                                    max_bet,
                                    home_price, away_price, handicap)
                                    VALUES
                                    ({0}, {1}, {2}, {3},
                                    {4}, {5}, "{6}",
                                    {7},
                                    {8}, {9}, {10});
                                    '''.format(
                                    payload['sportId'], league['id'], event['id'], period['number'],
                                    line_id, payload['ostime'], period['cutoff'],
                                    period['maxSpread'],
                                    spread['home'], spread['away'], spread['hdp'])
                        c.execute(sql_query)
                        conn.commit()
                if 'teamTotal' in period:
                    tTotal = period['teamTotal']
                    line_id = period['lineId']
                    for team in ['home', 'away']:
                        data = tTotal[team]
                        if data == None:
                            continue
                        sql_query = u''' -- new entry
                                    INSERT INTO odds_team
                                    (sport_id, league_id, event_id, match_period,
                                    line_id, time_stamp, cutoff_time,
                                    max_bet,
                                    team_name, over_price, under_price, points)
                                    VALUES
                                    ({0}, {1}, {2}, {3},
                                    {4}, {5}, "{6}",
                                    {7},
                                    "{8}", {9}, {10}, {11});
                                      '''.format(
                                    payload['sportId'], league['id'], event['id'], period['number'],
                                    line_id, payload['ostime'], period['cutoff'],
                                    period['maxTeamTotal'],
                                    team, data['over'], data['under'], data['points'])
                        # print sql_query
                        c.execute(sql_query)
                        conn.commit()
    if 'last' in payload:
        set_last_update(payload['sportId'], 'odds', payload['last'])


def pull_test():
    sql_query = """SELECT * FROM league"""
    print sql_query
    c.execute(sql_query)
    sport_id = c.fetchall()
    print sport_id

# pull_test()

def get_sport(league_id):
    print "Get sport for league", league_id
    assert is_valid_league(league_id)
    if isinstance(league_id, int): league = [league_id]
    else: league = league_id
    sql_query = """SELECT sport_id FROM league WHERE league_id IN ({0})""".format(', '.join(map(str, league)))
    # print sql_query
    c.execute(sql_query)
    result = c.fetchall()
    # print sport_id
    if result == []:
        return None
    sport_id = list(set([x[0] for x in result]))
    # print sport_id
    assert len(sport_id) <=1
    # print sport_id
    return sport_id[0]

def make_url(sport_id, info_type, last_update = None):
    assert isinstance(sport_id, int)
    '''
    New version for sport-based queries
    '''
    if last_update == None:
        pass
        #time.sleep(61)
    else:
        pass
        #time.sleep(6)
    info_urls = {'sports': 'v2/sports',
                 'leagues': 'v2/leagues',
                 'periods': 'v1/periods',
                 'fixtures': 'v1/fixtures',
                 'odds': 'v1/odds',
                 'settled': 'v1/fixtures/settled'}
    assert info_type in info_urls
    print "Make URL for sport:", sport_id, info_type
    time.sleep(2)
    assert isinstance(sport_id, int)
    url = pinn_path + info_urls[info_type]
    url += "?sportid=" + str(sport_id)
    if info_type == 'odds':
        url += "&oddsFormat=Decimal"
    if last_update != None:
        url += "&since=" + str(last_update)
    return url

'''
==========================================================
          Functions to support user interface
==========================================================
'''

def pretty_print(payload):
    print dumps(payload, indent = 2, separators = (',', ': '))


def change_sports():
    pinnacle_sports = get_sports()
    print "Sports available at Pinnacle:"
    for x in [y for y in pinnacle_sports if y['hasOfferings'] == True]:
        print ">>", x['name'], x['id']
    # get list of sports in the DB now
    c.execute('''SELECT * FROM sport''')
    db_sports = c.fetchall()
    #print db_sports
    print "Sports in the DB"
    for x in db_sports:
        print ">>", x[1], x[0]
    db_sport_ids = [x[0] for x in db_sports]
    #print db_sport_ids
    valid_sports = [y['id'] for y in pinnacle_sports if y['hasOfferings'] == True and y['id'] not in db_sport_ids]
    #print valid_sports
    response = int(raw_input("Enter sport to add:\n(0 to exit)\n>> "))
    if response in valid_sports:
        selected_sport = [x for x in pinnacle_sports if x['id'] == response][0]
        print selected_sport
        c.execute('''INSERT INTO sport (sport_id, name, scrape) VALUES ({0}, "{1}", {2})'''.format(
                selected_sport['id'], selected_sport['name'], 1))
        conn.commit()

def get_leagues_in_DB(sport_id):
    '''
    Returns a list of ints
    of IDs of leagues in the DB
    for that sport
    '''
    assert isinstance(sport_id, int)
    sql_query = '''SELECT league_id FROM league WHERE sport_id = {0};'''.format(sport_id)
    c.execute(sql_query)
    leagues_in_DB = [x[0] for x in c.fetchall()]
    return leagues_in_DB

def ensure_leagues_in_DB(sport_id, league_list):
    leagues_in_DB = get_leagues_in_DB(sport_id)
    unlogged_leagues = [x for x in league_list if x['id'] not in leagues_in_DB]
    for league in unlogged_leagues:
        c.execute(u''' --
                  INSERT INTO league (league_id, name, scrape, home_team_type, sport_id)
                  VALUES ({0}, "{1}", 1, "{2}", {3})'''.format(
                  league['id'], league['name'], league['homeTeamType'], sport_id))
    conn.commit()

def get_last_update(sport_id, query_type):
    pass
    '''
    New version, operates on a sport_id basis
    '''
    sql_query = u''' --
                SELECT last_update
                FROM last_sport_update
                WHERE sport_id = {0} AND
                      query_type = "{1}";
                '''.format(
                sport_id, query_type)
    c.execute(sql_query)
    sql_result = c.fetchall()
    if sql_result == []:
        return None
    else:
        return sql_result[0][0]

def set_last_update(sport_id, query_type, last_update, next_update = 'null'):
    pass
    '''
    New version, operates on a sport_id basis
    '''
    sql_query = u''' --
                INSERT OR REPLACE INTO last_sport_update
                (sport_id, query_type, last_update, next_update)
                VALUES
                ({0}, "{1}", {2}, {3})
                '''.format(
                sport_id, query_type, last_update, next_update)
    c.execute(sql_query)
    conn.commit()


def scrape_sport(sport_id):
    assert isinstance(sport_id, int)
    sql_query = '''SELECT sport_id FROM sport WHERE scrape = 1;'''
    c.execute(sql_query)
    result = [x[0] for x in c.fetchall()]
    if sport_id not in result:
        print "Can't scrape sport", sport_id
    else:
        print "Scraping sport", sport_id
    sport_leagues = get_leagues(sport_id)
    '''
    Make sure that all leagues are in the DB
    (removed: all leagues with offerings)
    '''
    # active_leagues = [x for x in sport_leagues if x['hasOfferings'] == True]
    # ensure_leagues_in_DB(sport_id, active_leagues)
    ensure_leagues_in_DB(sport_id, sport_leagues)
    # active_league_ids = [x['id'] for x in active_leagues]
    fixtures = get_fixtures(sport_id)
    # print dumps(a2, indent = 2, separators = (',', ': '))
    log_fixtures(fixtures)
    #
    odds = get_odds(sport_id)
    # print dumps(odds, indent = 2, separators = (',', ': '))
    log_odds(odds)
    settled = get_settled_fixtures(sport_id)
    log_settled_fixtures(settled)

# scrape_sport(22)
#pretty_print(a1)
#print type(a1)

def scrape_sport_interface():
    print "Please select a sport:"
    sql_query = '''SELECT sport_id FROM sport WHERE scrape = 1;'''
    c.execute(sql_query)
    result = [x[0] for x in c.fetchall()]
    print result
    response = int(raw_input(">> "))
    assert response in result
    scrape_sport(response)

def scrape_all():
    print "Scraping all sports"
    sql_query = '''SELECT sport_id FROM sport WHERE scrape = 1;'''
    c.execute(sql_query)
    result = [x[0] for x in c.fetchall()]
    for x in result:
        scrape_sport(x)

'''
==========================================================
          Functions to support user interface
==========================================================
'''
def main_menu():
    print "\nSelect an option:"
    print "0: Exit"
    print "1: Get/add sports"
    # print "2: Get/add leagues"
    # print "3: Scrape league"
    print "4: Scrape sport"
    print "5: Scrape all"
    response = raw_input(">> ")
    print ""
    if response == "1":
        change_sports()
    elif response == "2":
        pass
        #change_league()
    elif response == "3":
        pass
        #scrape_league_interface()
    elif response == "4":
        scrape_sport_interface()
    elif response == "5":
        scrape_all()
    return response

if RUN_MODE == "dev":
    while(True):
        result = main_menu()
        if result == "0":
            conn.close()
            break
        elif result == "-1":
            break
elif RUN_MODE == "prod":
    scrape_all()
    with open(source_path + "log.log", "a") as f:
        f.write(time.strftime('%X %x %Z') + '\n')
else:
    pass
