This implementation based on the fitbit-collect module from of David Gibbs (https://github.com/davgibbs/fitbit-collect). I especially used his module `gather_keys_oauth2.py` and his step-by-step instructions from his blog (https://davgibbs.com/how-to-get-fitbit-with-python/).

Three points made me not just adopt his implementation:
1. My focus was mainly on the data-sampling part, for visualization I use tools as Grafana.
2. I do not really use virtual environments, so I changed this part.
3. (and most importantly) The authentication step broke because of the line `cherrypy.quickstart(self)` in `gather_keys_oauth2.browser_authorize()`. This behaviour has been reproducable, the process always stopped in the `wspbus.Bus.block`-module (invoked by `cherrypy.quickstart`), waiting for all threads to exit, except the main thread. The corresponding log message has been `ENGINE Waiting for thread Thread-6`. Googling showed, that several people had/have this problem (in multiple contexts), but no proposed solution worked for me. So I adapted the `gather_keys_oauth2.browse_authorize()` function - basically by replacing the `cherrypy.quickstart()` line by the corresponding code, except for the for-loop from `wspbus.Bus.block`, which causes the error. 

This actually works. But: I do not have any experiences with handling different threads, and I am pretty sure, that this "waiting for all threads to exit" is important. So deleting this part is really my ugly workaround, which works in this case - but I would not use it in any "important" usecases. 

With that said, to the important part:

# Fitbit Data Sampler
A script to collect Fitbit data from your Fitbit account.

If you own a Fitbit, your data is likely available in your online account. Fitbit offers an API so that you can retreive this data and analyse it yourself. While `gather_keys_oauth2.py` runs through the steps needed to access the API, `sample_data.py` actually gets your data from the fitbit server. It makes use of the unofficial Fitbit client for Python https://github.com/orcasgit/python-fitbit

More details are in Davids blog post https://davgibbs.com/how-to-get-fitbit-with-python/

## Steps
1. After "git clone" on this repo, start by installing dependencies:
```bash
     pip install -r requirements.txt
```

2. Next login to your Fitbit account and create a new application at the URL https://dev.fitbit.com/apps/new.
Fill in details in the form as appropriate. Many of the details are not too important, but ensure that the "OAuth 2.0 Application Type is "Personal" and that the callback URL is "http://127.0.0.1:8080/"
The callback URL will be used to receive the token and secret later on.

3. After completing the form your application "OAuth 2.0 Client ID" and "Client Secret" should be displayed.
OAuth 2.0 Client Id is 6 characters and Client Secret is 32 characters. Copy them from the screen and place them as inputs for the `gather_keys_oauth2.main()` function:
```python
    from fitbit_data_sampler import gather_keys_oauth2
    gather_keys_oauth2.main(Id, Secret)
```
This script opens a new browser window. Look inside the script output for the URL that you need. Copy that link into your browser. The link is to confirm that you, as a user, want to give access to the your application to your data. Select all options and then "OK".

As part of the output of this script, two files are written to "client_details.json" and "user_details.json". These files will be used for accessing user data

4. Finally use the other script in the directory to sample data for a specific date. This script will read the content of the two details files and query the Fitbit API:
```python
    from fitbit_data_sampler import sample_data
    sample_data.sample_data('2020-12-24')
```
Note, that the date-format ist mandatory. 

It will then add the sampled data to several `.csv` files and stores them in a given folder (if not further specified: `data`). At the moment, the script samples all intraday-data, your sleep data and your body-weight (if this is not tracked, it is ignored). Might be extended in future.

## Refreshing tokens
Automatically tokens expire after 8 hours. The Fitbit application handles this expiration but renewing the tokens and updating the user_details.json file. In this way, you will not have to authenticate again.

## API
Explore the Fitbit API here: https://dev.fitbit.com/build/reference/web-api/explore/







