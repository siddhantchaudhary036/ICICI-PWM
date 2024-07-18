from SmartApi import SmartConnect
import pyotp
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import urllib
import time
from pyotp import TOTP
import requests
import json
import time
from breeze_connect import BreezeConnect
from datetime import datetime, timedelta
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pytz
from api_keys import icici_direct_key,icici_direct_secret,smartApi_key,icici_direct_totp,icici_direct_username,icici_direct_pass,smartApi_pwd,smartApi_token,smartApi_username

with open('BSEScripMaster.txt') as f:
    BSE_scrip_df = pd.read_csv(f, delimiter=',')


def autologin():

    API_KEY = icici_direct_key
    url = "https://api.icicidirect.com/apiuser/login?api_key="+urllib.parse.quote_plus(API_KEY)
    driver_path = 'chromedriver.exe' # make this '/your_user/your_directory/ICICI-PWM/chromedriver' if you are using a ubuntu server (you may also need to setup swap space if your ubuntu server has little RAM like mine did.)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")

    service = Service(executable_path = driver_path)
    browser = webdriver.Chrome(service = service, options=chrome_options)

    browser.get(url)
    time.sleep(1)

    userID = icici_direct_username
    totp = icici_direct_totp
    p1 = icici_direct_pass
    

    username = browser.find_element(By.ID,'txtuid')
    username.send_keys(userID)
    password = browser.find_element(By.ID,'txtPass')
    password.send_keys(p1)
    browser. find_element ("xpath", '/html/body/form/div[2]/div/div/div[1]/div[2]/div/div[4]/div/input').click()
    browser. find_element ( "xpath", '/html/body/form/div[2]/div/div/div[1]/div[2]/div/div[5]/input[1]').click()
    time.sleep (2)
    pin = browser.find_element( "xpath", '/html/body/form/div[2]/div/div/div[2]/div/div[2]/div[2]/div[3]/div/div[1]/input')
    totp = TOTP(totp)
    token = totp.now()
    pin.send_keys(token)
    browser.find_element("xpath", '/html/body/form/div[2]/div/div/div[2]/div/div[2]/div[2]/div[4]/input[1]'). click()
    time.sleep (1)
    temp_token=browser.current_url.split( 'apisession=') [1][ :8]
    browser.quit()

    return temp_token



def login_to_apis():
    """LOGIN TO ICICI DIRECT TO GET I_CLICK_2_GAIN FEED"""

    # Your credentials
    API_KEY = icici_direct_key
    API_SECRET = icici_direct_secret
    breeze = BreezeConnect(api_key=API_KEY)

        
    s = autologin()
    with open('Session_key.txt', 'w') as f:
        f.write(s)

    print('GENRATED NEW SESSION KEY')
    breeze.generate_session(api_secret=API_SECRET,
                            session_token=s)
            

    '''LOGIN TO ANGLE ONE API TO EXECUTE ORDERS'''

    # setting up secrets
    api_key = smartApi_key
    username = smartApi_username
    pwd = smartApi_pwd
    token = smartApi_token

    #initializing angel one
    smartApi = SmartConnect(api_key)
    totp = pyotp.TOTP(token).now()
    correlation_id = "abcde"
    data = smartApi.generateSession(username, pwd, totp)
        # login api call
    authToken = data['data']['jwtToken']
    refreshToken = data['data']['refreshToken']
        # fetch the feedtoken

    feedToken = smartApi.getfeedToken()
        # fetch User Profile
    res = smartApi.getProfile(refreshToken)
    smartApi.generateToken(refreshToken)
    res=res['data']['exchanges']

    internal_positions = {}
    initial_cash = float(smartApi.rmsLimit()['data']['availablecash'])
    print(initial_cash)

    return smartApi,breeze,initial_cash


def map_security_to_standard_format(stock_name):
    '''Finds the standard format ticker symbol for the given stock name'''
    stock_name_lower = stock_name.lower()
    BSE_scrip_df_lower = BSE_scrip_df['CompanyName'].str.lower()
    return BSE_scrip_df[BSE_scrip_df_lower == stock_name_lower]['ScripID'].values[0]


def validate_trade_conditions(ticker, action_type,order_type,recommended_price):
    '''this for now just returns true but we can edit this later to see wether certain internal conditions are met before entering a trade'''
    return True


def order_params_format(ticker,exchange,transaction_type,order_type,product_type,quantity,stock_description): 


    #FETCHING JSON DATA & CREATING DATAFRAME
    url = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
    d = requests.get(url).json()
    df = pd.DataFrame.from_dict(d)

    #FETCHING TICKER INFO FROM DATAFRAME BASED ON THE FOLLOWING PARAMETRS
    filtered_df = df[(df['name'] == (ticker)) & (df['exch_seg'] == exchange) & (df['instrumenttype']=="") & (df['symbol']==(ticker+'-EQ'))]
    result_list = filtered_df.to_dict(orient='records')
    result_dict = result_list[0]

    #ASSIGNING TICKER INFO TO ORDER PARAMETERS FOR LATER USE IN EXECUTION
    order_param_dict = {"variety":"NORMAL",
                      "tradingsymbol":result_dict['symbol'],
                      "symboltoken":result_dict['token'],
                      "transactiontype":transaction_type,
                      "exchange":exchange,
                      "ordertype": order_type,
                      "producttype": product_type,
                      "duration": "DAY",
                      "price": "0",
                      "squareoff": "0",
                      "stoploss": "0",
                      "quantity": quantity}
    return order_param_dict  

def find_available_quantity(token,action_type,stock_description):

    if 'margin' in stock_description.lower():
        available_position = 0    
        positions = smartApi.position()['data']
        
        for i in range(len(positions)):
            if positions[i]['symboltoken'] == str(token):
                available_position = abs(int(positions[i]['sellqty'])-int(positions[i]['buyqty']))
                break
        return available_position



def calculate_quantity(recommended_update,token,product_type,action_type,stock_description):


    if recommended_update.strip()=="":
      '''FIRST WE NEED TO FETCH HOW MUCH MARGIN WE CAN GET PER STOCK CONSIDERING WE ARE IN A INTRADAY SETUP??'''
      margin= float(smartApi.getMarginApi(params={"positions": [{
               "exchange": "NSE",
               "qty": 1,
               "price": "",
               "productType": product_type,
               "token": str(token),
               "tradeType": action_type.upper()
          }]})['data']['totalMarginRequired'])
      
      cash = initial_cash * invest_per_trade # Since we only want to invest 1/3 of total cash here
      quantity = int(round((cash/margin)))
      return quantity


    
    if "Partial" in recommended_update:
        available_position = find_available_quantity(token,action_type,stock_description)
        quantity = int(round(available_position/2))
        return quantity
    
    if "Full" in recommended_update:
        available_position = find_available_quantity(token,action_type,stock_description)
        quantity = int(available_position)
        return quantity
    
    if "Exit" in recommended_update:
        available_position = find_available_quantity(token,action_type,stock_description)
        quantity = int(available_position)
        return quantity
    
    if "SLTP" in recommended_update:
        available_position = find_available_quantity(token,action_type,stock_description)
        quantity = int(available_position)
        return quantity
    
    if "TGT" in recommended_update:
        available_position = find_available_quantity(token,action_type,stock_description)
        quantity = int(available_position)
        return quantity

def place_trade (ticker,action_type,stock_description,recommended_update,order_type,product_type,exchange):
    if recommended_update.strip() == '': # This is when we will place new orders
        if action_type.upper() == 'BUY':
            transaction_type = 'BUY'
        else:
            transaction_type = 'SELL'

        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')
        smartApi.placeOrder(order_parameters)
        print ('ORDER PLACED!!!')
        


    if 'Partial' in recommended_update: # This is when we have to sell half of our existing position (for a profit)
        if action_type.upper() == 'BUY':
            transaction_type = 'SELL'
        else:
            transaction_type = 'BUY'

        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')
        smartApi.placeOrder(order_parameters)
        print ('PARTIAL PROFIT!!!')
        


    if 'Full' in recommended_update: # This is when we have to sell all our existing position (for a profit)
        if action_type.upper() == 'BUY':
            transaction_type = 'SELL'
        else:
            transaction_type = 'BUY'

        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')
        smartApi.placeOrder(order_parameters)
        print ('FULL PROFIT!!!')
        


    if 'SLTP' in  recommended_update: # This is when we have to sell all our existing position (for a LOSS, STOPLOSS hit)
        if action_type.upper() == 'BUY':
            transaction_type = 'SELL'
        else:
            transaction_type = 'BUY'

        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')
        smartApi.placeOrder(order_parameters)
        print ('SLTP!!!')
        


    if 'Exit' in recommended_update: # This is when we have to sell all our existing position (for a LOSS)
        if action_type.upper() == 'BUY':
            transaction_type = 'SELL'
        else:
            transaction_type = 'BUY'
            
        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')
        smartApi.placeOrder(order_parameters)
        print ('EXITED!!!')

    if 'TGT' in recommended_update: #THIS is when we hit price target
        if action_type.upper() == 'BUY':
            transaction_type = 'SELL'
        else:
            transaction_type = 'BUY'

        order_parameters = order_params_format(ticker,exchange,transaction_type,order_type,product_type,1,stock_description)
        print('Stock correctly identified and order parameters generated')
        quantity = calculate_quantity(recommended_update,order_parameters['symboltoken'],product_type,transaction_type,stock_description)
        print('quantity identified')
        order_parameters['quantity'] = quantity
        print(f'ORDER PARAMS: {order_parameters}')

        smartApi.placeOrder(order_parameters)
        print ('TARGET HIT!!!')



# Callback to receive ticks.
def on_ticks(ticks):
    target_time = datetime.now(ist).replace(hour=9, minute=16, second=0, microsecond=0)
    current_time = datetime.now(ist)
    if current_time < target_time:
        print("IT IS NOT 9.16 YET MUST WAIT FOR MARKET TO OPEN OTHERWISE ORDER WILL BE REJECTED.")
        time_diff = (target_time - current_time).total_seconds()
        print(f"Sleeping for {time_diff} seconds until 9:16 AM IST.")
        time.sleep(time_diff)

    else:

        if ticks['iclick_status'] == 'open' and 'margin' in ticks['stock_description'].lower(): # or 'momentum' in ticks['stock_description'].lower()): 
            print(f"STOCK_DESCRIPTION: {ticks['stock_description']} ==> TICK FROM SERVER: {ticks}")
            stock_name = ticks['stock_name'].split('(')[0]
            action_type = ticks['action_type']
            stock_description = ticks['stock_description']
            recommended_price = [ticks['recommended_price_from'],ticks['recommended_price_to']]
            recommended_update = ticks['recommended_update']
            ticker = map_security_to_standard_format(stock_name) # ICICI bank gives weird ticker symbols to their stocks. We need the standard ticker symbol to place a order at Angle one.

            # Some more information for ANGLE ONE that I am hard coding for now since we are only trading margin equities
            if stock_description == 'Margin':
                exchange = "NSE" 
                product_type = "INTRADAY"
                order_type = 'MARKET'
            

            if validate_trade_conditions(ticker,action_type,stock_description,recommended_price) == True: # Check if my internal trade conditions are met before placing an order
                place_trade (ticker,action_type,stock_description,recommended_update,order_type,product_type,exchange)
                


ist = pytz.timezone('Asia/Kolkata')
invest_per_trade = 0.25
start_time = datetime.now(ist).replace(hour=9,minute=15,second=1,microsecond=0)
# Assign the callbacks.

while True:
    time.sleep(1) # To lower CPU stress
    if datetime.now(ist)>start_time:
        smartApi,breeze,initial_cash = login_to_apis()
        breeze.ws_connect()
        breeze.on_ticks = on_ticks
        # subscribe order notification feeds(it will connect to order streaming server)
        breeze.subscribe_feeds(get_order_notification=True)
        breeze.subscribe_feeds(stock_token = "i_click_2_gain")
        print('subscribed')
        end_time = datetime.now(ist).replace(hour=16,minute=0,second=0,microsecond=0)
        while True:
            if datetime.now(ist)>end_time:
                start_time += timedelta(days=1) 
                breeze.unsubscribe_feeds(stock_token = "i_click_2_gain")
                breeze.ws_disconnect()
                break
            x=1
    
