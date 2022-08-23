import numpy as np
import pandas as pd

MOD_WEIGHTS = {
    'Original': {
        'Limited Wardrobe': 0.8,
        'Just Learnt The Basics': 0.8,
        'Strange Choice': 0.5,
        'Lore Reader': 0.6,
        'Blind': 0.2,
        'Half Power': 0.4,
        "Petra's Run": 0.6,
        'Solo': 1,
        'Fireteam': 0
    },
    'New': {
        'Limited Wardrobe': 0.7,
        'Just Learnt The Basics': 0.6,
        'Strange Choice': 0.2,
        'Lore Reader': 0.6,
        'Blind': 0.4,
        'Half Power': 0.6,
        "Petra's Run": 0.6,
        'Solo': 1,
        'Fireteam': 0
    }
}

TIME_WEIGHTS = {
    'Original': {
        45*60: -0.2,
        40*60: 0,
        35*60: 0.7,
        30*60: 0.8,
        25*60: 0.9,
        0: 1
    },
    'New': {
        45*60: -0.2,
        40*60: 0,
        35*60: 0.6,
        30*60: 0.7,
        25*60: 0.8,
        0: 0.9
    }
}

MOD_SET = 'New'
MOD_WEIGHT = MOD_WEIGHTS[MOD_SET]
TIME_WEIGHT = TIME_WEIGHTS[MOD_SET]

SIGMOID_K = -0.025 # (1 in 40 steepness)
SIGMOID_MID = 200

KILL_MAX = 480
KILL_SCORE = 1
DEATH_MAX = 10
DEATH_COST = 20

def calculate_score(record):

    # split out modifiers from responses
    mods = list()
    if record['loadout_mods']:
        loadout_mods_split = record['loadout_mods'].split(';')
        mods += loadout_mods_split

    if record['handicap_mods']:
        handicap_mods_split = record['handicap_mods'].split(';')
        mods += handicap_mods_split

    if record['difficulty_mods']:
        difficulty_mods_split = record['difficulty_mods'].split(';')
        mods += difficulty_mods_split
    
    if not record['is_flawless']:
        if "Petra's Run" in mods:
            mods.remove("Petra's Run")

    if record['guardians'] > 1:
        if 'Solo' in mods:
            mods.remove('Solo')
        if not 'Fireteam' in mods:
            mods.append('Fireteam')
    else:
        if 'Fireteam' in mods:
            mods.remove('Fireteam')
        if not 'Solo' in mods:
            mods.append('Solo')

    kills_counted = min(record['kills'], KILL_MAX)
    deaths_counted = min(record['deaths'], DEATH_MAX)

    kills_scored = KILL_MAX / (1 + np.exp(SIGMOID_K*(kills_counted - SIGMOID_MID)))
    #deaths_scored = DEATH_MAX / (1 + np.exp(SIGMOID_K*(deaths_counted - SIGMOID_MID)))
    deaths_scored = min(deaths_counted, DEATH_MAX)
    base_score = (KILL_SCORE * kills_scored) - (DEATH_COST * deaths_scored)

    base_multiplier = 1
    mod_multiplier = 0
    for mod in mods:
        mod_multiplier += MOD_WEIGHT[mod]
    
    time_scored = record['time_sec']
    time_bracket = 0
    for bracket in sorted(TIME_WEIGHT.keys()):
        if time_scored > bracket:
            time_bracket = bracket
    time_multiplier = TIME_WEIGHT[time_bracket]

    total_multiplier = base_multiplier + mod_multiplier + time_multiplier
    score = base_score * total_multiplier

    return base_score, total_multiplier, score

def main():
    
    df = pd.read_csv('results.csv')
    df['loadout_mods'].fillna('', inplace=True)
    df['handicap_mods'].fillna('', inplace=True)
    df['difficulty_mods'].fillna('', inplace=True)
    
    bases = list()
    mults = list()
    scores = list()
    for idx, record in df.iterrows():
        base, multiplier, score = calculate_score(record)
        bases.append(base)
        mults.append(multiplier)
        scores.append(score)
    
    df['base_score'] = pd.Series(bases)
    df['total_multiplier'] = pd.Series(mults)
    df['score'] = pd.Series(scores)
    df.sort_values(by='score', ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'position'}, inplace=True)
    df['position'] += 1
    
    print(df)
    df.to_csv('results_output.csv')

if __name__ == '__main__':
    main()