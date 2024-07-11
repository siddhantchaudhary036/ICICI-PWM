# ICICI-PWM
Automating trade execution using broker Angle One API for all intraday order calls/recommendations made by ICICI Direct's I Click2Gain tool.
For this, you will need to have an account at both ICICI Direct and Angle One. ICICI direct for their recommendations and Angle one for the execution of orders.

All you need to do is update the api_keys file and run the file_run.py on your computer, after this as long as your computer/server is running your orders will automatically keep on getting sent. :) You could also just run main.py directly using scheduler software like corn :)

We have 6 different files:

main.py: (this is where all of the internal logic of connecting to the broker APIs, subscribing to the I-Click-2-Gain WebSocket, and executing orders is done.) This file will execute all intraday equity order calls made by I-Click-2-Gain.

file_run.py: (this is the file that manages running and rerunning main.py) This file is required since after 24 hours the ICICI direct session key needs to be updated, the initial_cash variable which shows how much funds are currently available to trade with needs to be updated, this allows us to compound our money. The WebSocket is resubscribed which is necessary else it leads to timeout from the ICICI direct server endpoint.

Session_key.txt: (this is the file that will contain the recent most copy of your session key from ICICI direct. You may leave this file untouched and empty it will automatically be managed by main.py)

api_keys.py: (this file is currently empty but you need to add the following variables to it, with of course your own API keys:- 
icici_direct_key = "" 
icici_direct_secret = "" 
icici_direct_username = ''
icici_direct_totp = ''
icici_direct_pass = ''
smartApi_key = '' 
smartApi_token = "" 
smartApi_pwd = '' 
smartApi_username = ''

BSEScripMaster.txt: This file allows for the mapping of company names to their BSE scrips. You may need to update this file every once in a while with the latest versions. You may fetch the latest version on BSE's website as a CSV file and convert it to a text file.

chromedriver.exe: This is the driver for the selenium function that auto logs in to ICICI directly to get the updated session key.
