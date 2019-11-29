-- ============================================
--                    ToDo
-- ============================================

-- ============================================
--  sport/league/event/etc info storage tables
-- ============================================

CREATE TABLE sport (
sport_id INT PRIMARY KEY, -- API: id
name TEXT, -- API: name
has_offerings INT, -- Booean
scrape INT -- Boolean
);

CREATE TABLE league (
league_id INT PRIMARY KEY, -- API: id
name TEXT, -- API: name
sport_name TEXT, -- user defined e.g. LoL, CS:GO
league_info_1 TEXT, -- user-defined
league_info_2 TEXT,
league_info_3 TEXT,
has_offerings INT, -- Boolean
scrape INT, -- Boolean (unused?)
home_team_type TEXT NOT NULL, -- From get_leagues
sport_id INT NOT NULL,
FOREIGN KEY (sport_id) REFERENCES sport(sport_id)
);

CREATE TABLE event ( -- a game / match / bout
event_id INT PRIMARY KEY,
sport_id INT, -- optional
league_id INT NOT NULL,
tags TEXT, -- user defined. e.g. game 1 / 2 / 3, UFC/TUF/Fight Night
conditions TEXT, -- user defined (e.g. 1st to 5, 1st Blood)
event_info_1 TEXT,
event_info_2 TEXT,
start_time TEXT,
home_name TEXT,
away_name TEXT,
event_title TEXT, -- user-defined, e.g. UFC 217 or LoL Worlds, not unique
betting_status TEXT, -- 'O' Open, 'H' on hold, 'I' reduced betting
FOREIGN KEY (league_id) REFERENCES league(league_id)
);

CREATE TABLE period ( -- part of or a whole event
-- line_id INT, -- API: lineId, changes often
sport_id INT, -- optional
league_id INT, -- optional
event_id INT NOT NULL,
match_period INT NOT NULL, -- API: number. 0 (game), 1/2 (halves)
period_info_1 TEXT,
period_info_2 TEXT,
cutoff_time TEXT, -- API: cutoff
settled_status INT DEFAULT 0, -- API: settled/status 1 to 5 (various meanings)
settled_id INT, -- API: settled/settlementID
settled_time TEXT, -- API: settled/settledAt
team_1_score, -- need to map team1 to home or away
team_2_score,
winning_team TEXT, -- Int? Text? user-calculated.
cancellation_details TEXT, -- dunno if I'll use this
PRIMARY KEY (event_id, match_period),
FOREIGN KEY (event_id) REFERENCES event(event_id)
);

-- ============================================
--       Might put some code here to give
--    teams / athletes an ID and track them
-- ============================================

-- ============================================
-- Handling when the leagues were last updated
-- ============================================

CREATE TABLE last_sport_update(
-- This will operate on a sport basis
sport_id INT NOT NULL,
query_type TEXT NOT NULL, -- "fixtures", "settled", "odds"
last_update INT NOT NULL, -- API: last
next_update REAL, -- os time of next allowable update (i.e. t + 5 or t + 60)
PRIMARY KEY (sport_id, query_type),
FOREIGN KEY (sport_id) REFERENCES sport(sport_id)
);

/*
CREATE TABLE last_update (
-- This will operate on a league basis
query_type TEXT NOT NULL, -- "fixtures", "settled", "odds"
last_update INT NOT NULL, -- API: last
next_update REAL, -- os time of next allowable update (i.e. t + 5 or t + 60)
league_id INT NOT NULL,
sport_id INT NOT NULL,
PRIMARY KEY (league_id, query_type),
FOREIGN KEY (league_id) REFERENCES league(id),
FOREIGN KEY (sport_id) REFERENCES sport(id)
);
*/

-- ============================================
--   Tables to store results of odds queries
-- ============================================

CREATE TABLE odds_moneyline (
id INTEGER PRIMARY KEY AUTOINCREMENT, -- table-specific
sport_id INT, -- optional
league_id INT, -- optional
event_id INT NOT NULL,
match_period INT NOT NULL,
info_1 TEXT,
info_2 TEXT,
conditions TEXT, -- user defined (e.g. 1st Blood)
time_stamp REAL, -- user defined, os time (since 1970)
line_id INT NOT NULL, -- API: lineID [Note: This is already in period]
max_bet REAL, -- API: maxMoneyLine
cutoff_time TEXT,
home_price REAL NOT NULL,
away_price REAL NOT NULL,
draw_price REAL, -- not always used
FOREIGN KEY (event_id) REFERENCES event(event_id),
FOREIGN KEY (event_id, match_period) REFERENCES period(event_id, match_period)
);

CREATE TABLE odds_spread (
id INTEGER PRIMARY KEY AUTOINCREMENT, -- table-specific
sport_id INT, -- optional
league_id INT, -- optional
event_id INT NOT NULL,
match_period INT NOT NULL,
info_1 TEXT,
info_2 TEXT,
conditions TEXT, -- user defined (e.g. 1st Blood)
time_stamp REAL, -- user defined, os time (since 1970)
line_id INT NOT NULL, -- API: altLineID (takes precedence) or lineID (default)
max_bet REAL, -- API: maxSpread
cutoff_time TEXT,
home_price REAL NOT NULL,
away_price REAL NOT NULL,
handicap REAL NOT NULL,
FOREIGN KEY (event_id) REFERENCES event(event_id),
FOREIGN KEY (event_id, match_period) REFERENCES period(event_id, match_period)
);

CREATE TABLE odds_total (
id INTEGER PRIMARY KEY AUTOINCREMENT, -- table-specific
sport_id INT, -- optional
league_id INT, -- optional
event_id INT NOT NULL,
match_period INT NOT NULL,
info_1 TEXT,
info_2 TEXT,
conditions TEXT, -- user defined (e.g. 1st Blood)
time_stamp REAL, -- user defined, os time (since 1970)
line_id INT NOT NULL, -- API: altLineID (takes precedence) or lineID (default)
max_bet REAL, -- API: maxTotal
cutoff_time TEXT,
points REAL NOT NULL,
over_price REAL NOT NULL,
under_price REAL NOT NULL,
FOREIGN KEY (event_id) REFERENCES event(event_id),
FOREIGN KEY (event_id, match_period) REFERENCES period(event_id, match_period)
);

CREATE TABLE odds_team (
id INTEGER PRIMARY KEY AUTOINCREMENT, -- table-specific
sport_id INT, -- optional
league_id INT, -- optional
event_id INT NOT NULL,
match_period INT NOT NULL,
info_1 TEXT,
info_2 TEXT,
conditions TEXT, -- user defined (e.g. 1st Blood)
time_stamp REAL, -- user defined, os time (since 1970)
line_id INT NOT NULL, -- API: lineID
max_bet REAL, -- API: maxTeamTotal
cutoff_time TEXT,
team_name TEXT NOT NULL, -- 'home' or 'away'
points REAL NOT NULL,
over_price REAL NOT NULL,
under_price REAL NOT NULL,
FOREIGN KEY (event_id) REFERENCES event(event_id),
FOREIGN KEY (event_id, match_period) REFERENCES period(event_id, match_period)
);

