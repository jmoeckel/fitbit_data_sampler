"""
Script to retrieve Fitbit data for the given user
"""
import os
import json
import inspect
import pandas as pd 
import datetime

import fitbit # https://python-fitbit.readthedocs.io/en/latest/

dp_thisdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
CLIENT_DETAILS_FILE = os.path.join(dp_thisdir, 'client_details.json')  # configuration for for the client
USER_DETAILS_FILE = os.path.join(dp_thisdir, 'user_details.json')  # user details file

def refresh_callback(token):
    """
    This method is only called when the authenticate token is out of date
    and a new token has been issued which needs to be stored somewhere for
    the next run
    param (token): A dictionary with the new details
    """
    print('CALLBACK: The token has been updated since last run')
    with open(USER_DETAILS_FILE, 'w') as f:
        json.dump(token, f)
    print('Successfully written update refresh token')


def _get_user_details():
    """
    The specific user that you want to retrieve data for.
    """
    with open(USER_DETAILS_FILE) as f:
        fitbit_user = json.load(f)
        access_token = fitbit_user['access_token']
        refresh_token = fitbit_user['refresh_token']
        expires_at = fitbit_user['expires_at']

    return access_token, refresh_token, expires_at


def _get_client_details():
    """The client is the application which requires access"""
    with open(CLIENT_DETAILS_FILE) as f:
        client_details = json.load(f)
        client_id = client_details['client_id']
        client_secret = client_details['client_secret']

    return client_id, client_secret
    

def sample_data(sdate=None, dp_data=None):
    """ for a specific date, different data are sampled and stored in .csv 
    files
    
    At the moment, intraday-timeseries for heartrate, steps, distance, floor 
    and elevation as well as sleep-relevant data and the body-weight are 
    considered. 
    
    Timeseries are stored day-specific .csv files (and are overwritten, if the
    the same day is called more than once). Files are named "{sdate}_{activity}",
    where activity is replaced by different considered categories. 
    All summary data are stored in a single file called "daily_summary.csv". 
    New data are appended. 

    Parameters
    ----------
    sdate : str, optional
        specific date of interest, mandatory dateformat: "YYYY-MM-DD". If none,
        sdate is set to yesterday. The default is None.
    dp_data : str, optional
        Dirpath, where the sampled data should be stored as .csv files. If none,
        files are stored The default is None.

    Returns
    -------
    fitbit.Fitbit() 
        Fitbit object from the fitbit module. Just for fun. 

    """
    
    if not sdate:
       sdate = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not dp_data:
        dp_data = os.path.join(dp_thisdir, 'data')
        
    if os.path.isdir(dp_data):
        os.mkdir(dp_data)
    
    # connect to fitbit with given authentication
    client_id, client_secret = _get_client_details()
    access_token, refresh_token, expires_at = _get_user_details()

    fitti = fitbit.Fitbit(client_id, client_secret, oauth2=True,
                          access_token=access_token,
                          refresh_token=refresh_token, expires_at=expires_at,
                          refresh_cb=refresh_callback,
                          system='metric')
   
    # intraday activities
    activities = ['heart', 'steps', 'distance', 'floors', 'elevation']
    
    acties = []
    values = []
    dates = []
    
    for activity in activities: 
        # intraday
        js = fitti.intraday_time_series(f'activities/{activity}', base_date=sdate, detail_level='1min')
        
        intra = js[f'activities-{activity}-intraday']['dataset']
        
        data = [[e['time'], e['value']] for e in intra]
        df = pd.DataFrame(data=data, columns=['Time', 'Value'])

        df.to_csv(os.path.join(dp_data, f'{sdate}_{activity}.csv'), index=False)
    
    
        # Summary 
        summary = js[f'activities-{activity}'][0]
        
        if activity == 'heart':
            
            date = summary['dateTime']
            
            hrzs = summary['value']['heartRateZones']
            
            for hrz in hrzs:
                dates.append(date)                
                acties.append(hrz['name'] + ' - minutes')
                values.append(hrz['minutes'])
                
                dates.append(date)                
                acties.append(hrz['name'] + ' - calories')
                values.append(hrz['caloriesOut'])
            
        else:
            dates.append(summary['dateTime'])
            values.append(summary['value'])
            acties.append(activity.capitalize())
    
        
    df2 = pd.DataFrame({'Date': dates, 'Activity':acties, 'Value':values})
    df2['Category'] = 'Activity'
    df2 = df2[['Date', 'Category', 'Activity', 'Value']]        
    df2.to_csv(os.path.join(dp_data, 'daily_summary.csv'), mode='a', header=False, index=False)
        
           
    # sleep data intranight
    js = fitti.make_request(fr'https://api.fitbit.com/1.2/user/-/sleep/date/{sdate}.json')
    
    data =js['sleep'][0]['levels']['data']
    stime = [entry['dateTime'] for entry in data]
    level = [entry['level'] for entry in data]
    seconds = [entry['seconds'] for entry in data]
    df = pd.DataFrame({'Time':stime, 'Level':level, 'Seconds': seconds})
    df.to_csv(os.path.join(dp_data, f'{sdate}_sleep.csv'), header=True, index = False)
    
    
    # sleep data summary
    summary = js['summary']    
    acties = ['Stage - Deep', 'Stage - Light', 'Stage - REM', 'Stage - Wake', 'totalMinAsleep', 'totalMinBed']
    values = [summary['stages']['deep'],
              summary['stages']['light'],
              summary['stages']['rem'],
              summary['stages']['wake'],
              summary['totalMinutesAsleep'],
              summary['totalTimeInBed']]
    
    df = pd.DataFrame({'Activity': acties, 'Value': values})
    df['Date'] = sdate
    df['Category'] = 'Sleep'
    
    df = df[['Date', 'Category', 'Activity', 'Value']]     
    df.to_csv(os.path.join(dp_data, 'daily_summary.csv'), mode='a', header=False, index=False)                  
    
    
    # other
    js_weight = fitti.get_bodyweight(sdate)
    try:
        w = js_weight['weight'][0]['weight']
    except IndexError:
        print(f'no "weight" for {sdate}')
    else:    
        df = pd.DataFrame({'Date': [sdate], 'Category': ['Body'], 'Activity': ['Weight'], 'Value': [w]})
        df.to_csv(os.path.join(dp_data, 'daily_summary.csv'), mode='a', header=False, index=False)
    
    return fitti


def sample_data_period(date_start:str, dp_data=None):
    """ To sanple data from a data in the past until "yesterday"
    
    This is more or less just a wrapper for sample_data(). All dates, beginning
    with {date_start} are used as an input for sample_data(). Last call will
    be with "yesterday".
    
    Parameters
    ----------
    date_start : str
        specific date of interest, mandatory dateformat: "YYYY-MM-DD".
    dp_data : str, optional
        Dirpath, where the sampled data should be stored as .csv files. If none,
        files are stored The default is None.

    Returns
    -------
    None.

    """
    d0 = datetime.strptime(date_start, "%Y-%m-%d")
    d1 = datetime.datetime.now()
    
    dt = d1 - d0
    n = dt.days
    
    while n>0: 
        sday = str((datetime.datetime.now() - datetime.timedelta(days=n)).strftime('%Y-%m-%d'))  
        sample_data(sday)
        n = n-1
        