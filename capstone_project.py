import requests                 # for making HTTP requests
import json                     # library for handling JSON data
import time                     # module for sleep operation
import math
import statistics
from boltiot import Bolt        # importing Bolt from boltiot module
import capstone_conf            # config file

mybolt = Bolt(capstone_conf.bolt_api_key, capstone_conf.device_id)

print("Fridge Temperature Monitor\n")
threshold_max=int(input("Enter the Upper Temperature limit: "))             # Upper Threshold beyond which the alert should be sent
threshold_max=threshold_max*1024/100
threshold_min=int(input("Enter the Lower Temperature limit: "))            # Lower Threshold beyond which the alert should be sent
threshold_min=threshold_min*1024/100
print("Initiating temperature detection..\n")

def get_sensor_value_from_pin(pin):
    """Returns the sensor value. Returns -999 if request fails"""
    try:
        response = mybolt.analogRead(pin)
        data = json.loads(response)
        if data["success"] != 1:
            print("Request not successfull")
            print("This is the response->", data)
            return -999
        sensor_value = int(data["value"])
        return sensor_value
    except Exception as e:
        print("Something went wrong when returning the sensor value")
        print(e)
        return -999


def send_telegram_message(message):
    """Sends message via Telegram"""
    url = "https://api.telegram.org/" + capstone_conf.telegram_bot_id + "/sendMessage"
    data = {"chat_id": capstone_conf.telegram_chat_id,"text": message}
    try:
        response = requests.request("GET",url,params=data)
        print("This is the Telegram response")
        print(response.text)
        telegram_data = json.loads(response.text)
        return telegram_data["ok"]
    except Exception as e:
        print("An error occurred in sending the alert message via Telegram")
        print(e)
        return False

def compute_bounds(history_data,frame_size,factor):
    if len(history_data)<frame_size :
        return None

    if len(history_data)>frame_size :
        del history_data[0:len(history_data)-frame_size]
    Mn=statistics.mean(history_data)
    Variance=0
    for data in history_data :
        Variance += math.pow((data-Mn),2)
    Zn = factor * math.sqrt(Variance / frame_size)
    High_bound = history_data[frame_size-1]+Zn
    Low_bound = history_data[frame_size-1]-Zn
    return [High_bound,Low_bound]
    
history_data=[]

while True:
    #Step 1
    response = mybolt.analogRead('A0')
    print (response)
    data = json.loads(response)
    if data['success'] != 1:
        print("There was an error while retriving the data.")
        print("This is the error:"+data['value'])
        time.sleep(10)
        continue

    print ("This is the value "+str(100*int(data['value'])/1024)+" oC")
    sensor_value=0
    try:
        sensor_value = int(data['value'])
    except e:
        print("There was an error while parsing the response: ",e)
        continue

    bound = compute_bounds(history_data,capstone_conf.FRAME_SIZE,capstone_conf.MUL_FACTOR)
    if not bound:
        required_data_count=capstone_conf.FRAME_SIZE-len(history_data)
        print("Not enough data to compute Z-score. Need ",required_data_count," more data points")
        history_data.append(int(data['value']))
        time.sleep(10)
        continue

    try:
        if sensor_value > bound[0] :
            print ("The Temperature level Anomaly Detected.\nSomeone opened the Fridge Door!!")
            message="The Temperature level Anomaly Detected.\nSomeone opened the Fridge Door!!"
            telegram_status = send_telegram_message(message)
            print("This is the Telegram status:", telegram_status)
        elif sensor_value < bound[1]:
            print ("The Temperature level Anomaly Detected.\nSomeone opened the Fridge Door!!")
            message="The Temperature level Anomaly Detected.\nSomeone opened the Fridge Door!!"
            telegram_status = send_telegram_message(message)
            print("This is the Telegram status:", telegram_status)
        history_data.append(sensor_value);
    except Exception as e:
        print ("Error",e)
    time.sleep(10)
    
    # Step 2
    if sensor_value == -999:
        print("Request was unsuccessfull. Skipping.")
        time.sleep(10)
        continue
    
    # Step 3
    if sensor_value >= threshold_max:
        print("Sensor value has exceeded threshold")
        message = "Alert! Sensor value has exceeded " + str(100*threshold_max/1024) +" oC.\nThe current value is " + str(100*sensor_value/1024)+" oC"
        telegram_status = send_telegram_message(message)
        print("This is the Telegram status:", telegram_status)
     
    # Step 4
    if sensor_value <= threshold_min:
        print("Sensor value below threshold")
        message = "Alert! Sensor value has decreased below " + str(100*threshold_min/1024) +" oC.\nThe current value is " + str(100*sensor_value/1024)+" oC"
        telegram_status = send_telegram_message(message)
        print("This is the Telegram status:", telegram_status)

    # Step 5
    time.sleep(10)