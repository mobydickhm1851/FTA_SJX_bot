import requests 
from bs4 import BeautifulSoup 
import pandas as pd
from datetime import datetime
import time
import sys
import os
# login_url = "http://202.158.223.244/OPS_STUDENT_REPORTS/rdLogon.aspx" 
login_url = "http://202.158.223.244/OPS_STUDENT_REPORTS/rdPage.aspx" 


def date_time_to_min(date_lst, time_str):
    day_of_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # day_of_month_leap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DT = datetime(date_lst[0], date_lst[1], date_lst[2], int(time_str.split(':')[0]), int(time_str.split(':')[1]))
    ftr = [day_of_month[date_lst[1]]*86400, 86400, 0, 3600, 60]  # [mm, dd, yy, h, m]
    DT_lst = [DT.month, DT.day, DT.year, DT.hour, DT.minute]
    time_min = sum([a*b for a,b in zip(ftr, DT_lst)])
    return time_min

def create_message(name, add_num, del_num, flight_dict):

    msg_all = "{0} have {1} new flights \nand {2} cancelled flights. \nHere are your latest flight schedule. \n\n".format(name, add_num, del_num)


    if len(flight_dict['Time']) == 0:
        msg_all += "NO FLIGHT, CALL YOUR INSTRUCTOR!"

    for i in range(len(flight_dict['Time'])):
        date_lst = flight_dict['Date'][i]
        msg = str(date_lst[0])+'/'+str(date_lst[1])+'/'+str(date_lst[2])+'  '\
            + flight_dict['Time'][i] + '\n' + flight_dict['Captain'][i]+'  ' + flight_dict['Crew'][i]+'  '\
            + flight_dict['Aircraft'][i]+'\n' + flight_dict['Module'][i]+'-'+flight_dict['Exercise'][i]+'  '\
            + flight_dict['Description'][i]+'  ' + flight_dict['Flytype'][i]+'\n'+'\n'
        msg_all += msg
    msg_all += "http://202.158.223.244/OPS_STUDENT_REPORTS/rdLogon.aspx" + "\n"
    return msg_all

def send_LINE_notification(msg, tkn="SJX"):
    # Place your LINE Notify token here
    if tkn == "SJX":
        token = 'ukeljeZgqnHjnKCZWDOtP9OwY4lHeBWo4QuE59H7fEB' # SJX05
    elif tkn == "LiuYC":
        token = '8If5PUueJehCYhXXIfcvDkDkseleeR4Dx85Klbod2Lv'  # LiuYC

    # The API url of LINE Notify
    api_url = 'https://notify-api.line.me/api/notify'

    # Send the formatted datetime as a message that will be sent
    message = msg # <- Feel free to replace this with any kind of message that you want. For instance, 'Are you happy today ? Take care.'

    # Convert LINE Notify token to dictionary
    # token_dict = { 'Authorization': 'Bearer' + ' ' + token }
    token_dict = { 'Authorization': 'Bearer' + ' ' + token }

    # Convert message to dictionary
    msg_dict = { 'message': message }

    # # Place the image filename (Supported image format are png and jpeg, according to the LINE Notify API docs)
    # image = './my_image.jpg'
    # # Open the image in binary format for reading
    # binary = open(image, mode='rb')
    # # Convert your image file to dictionary
    # img_dict = { 'imageFile': binary }

    # Send the image and the message
    requests.post(
    api_url,            # <- Send to the API url : 'https://notify-api.line.me/api/notify'
    headers=token_dict, # <- Set the LINE Notify token to the headers (for authentication)
    data=msg_dict,      # <- Send your message through a LINE Notify account
    # files=img_dict      # <- Send your image through a LINE Notify account
    )


class SJX_cadet:
    def __init__(self, name, login, psw):
        self.name = name
        self.login = login
        self.password = psw
        self.flight_dict = dict()

    def request_update(self):
        with requests.session() as s: 
            req = s.get(login_url).text 
            html = BeautifulSoup(req,"html.parser")     
            dct=s.cookies.get_dict()

        payload = { 
            "rdUsername": self.login,
            "rdFormLogon": "True",
            "rdPassword": self.password,
            # "ASP.NET_SessionId":dct["ASP.NET_SessionId"],
            "Submit1": "Logon"
        }

        res = s.post(login_url, data=payload) 

        final = s.get(login_url)
        soup1 = BeautifulSoup(final.content, features="lxml")

        table = soup1.find("table")
        table_rows = table.find_all('tr')

        res = []
        for tr in table_rows:
            td = tr.find_all('td')
            row = [tr.text.strip() for tr in td if tr.text.strip()]
            if row:
                res.append(row)

        # TEMPORARY bug fix: Crew sometimes might be None (SOLO)
        for lst in res:
            if len(lst) == 7:
                lst.insert(2, 'SOLO')

        df = pd.DataFrame(res, columns=["Time", "Captain", "Crew", "Aircraft", "Module", "Exercise","Description", "Flytype"])

        course_dict = {
            "Date":[],
            "Time":[],
            "Captain":[],
            "Crew":[],
            "Aircraft":[],
            "Module":[],
            "Exercise":[],
            "Description":[],
            "Flytype":[]
        }

        date_lst = []
        for i in range(int(df['Time'].count())):       
            if df['Captain'][i] == None:
                lst = df["Time"][i].split("- ")[1].split("/")
                date_lst = [int(j) for j in lst]
            elif df['Captain'][i] == 'Captain':
                pass
            else: 
                for key in course_dict:
                    if key == "Date":
                        course_dict['Date'].append(date_lst)
                    else:
                        course_dict[key].append(df[key][i])
        
        return course_dict

    def check_change(self):
        new_dict = self.request_update()
        add_count = 0
        del_count = 0
        # if first time update, i.e., empty self.flight_dict
        if len(self.flight_dict['Time']) != 0:

            # check each flight if added or deleted
            old_flight_num = len(self.flight_dict['Time'])
            new_flight_num = len(new_dict['Time'])
            old_minute_lst = [date_time_to_min(self.flight_dict['Date'][i], self.flight_dict['Time'][i]) for i in range(old_flight_num)]
            new_minute_lst = [date_time_to_min(new_dict['Date'][i], new_dict['Time'][i]) for i in range(new_flight_num)]

            add_count = len(set(new_minute_lst) - set(old_minute_lst))
            del_count = len(set(old_minute_lst) - set(new_minute_lst))

            self.flight_dict = new_dict

        # empty self.flight_dict
        else: 
            self.flight_dict = new_dict

        # return numer of flight change, and change_dict
        return add_count, del_count, self.flight_dict 
    

        
        

if __name__ == "__main__":
    
    count = 0
    CM = SJX_cadet("Josh", "wang2004", "wang2004")
    OP = SJX_cadet("Jordan", "huang2004", "huang2004")
    DR = SJX_cadet("James", "liu2004", "liu2004")
    GC = SJX_cadet("Jason", "sheng2004", "sheng2004")
    
    CM.flight_dict = CM.request_update()
    OP.flight_dict = OP.request_update()
    DR.flight_dict = DR.request_update()
    GC.flight_dict = GC.request_update()


    while True:
        try:
            CM_a, CM_d, CM_dict = CM.check_change()
            if CM_a != 0 or CM_d != 0:
                message = create_message(CM.name, CM_a, CM_d, CM_dict)
                send_LINE_notification(message, tkn='SJX')

            
            OP_a, OP_d, OP_dict = OP.check_change()
            if OP_a != 0 or OP_d != 0:
                message = create_message(OP.name, OP_a, OP_d, OP_dict)
                send_LINE_notification(message, tkn='SJX')

            DR_a, DR_d, DR_dict = DR.check_change()
            if DR_a != 0 or DR_d != 0:
                message = create_message(DR.name, DR_a, DR_d, DR_dict)
                send_LINE_notification(message, tkn='SJX')

            GC_a, GC_d, GC_dict = GC.check_change()
            if GC_a != 0 or GC_d != 0:
                message = create_message(GC.name, GC_a, GC_d, GC_dict)
                send_LINE_notification(message, tkn='SJX')
            
            count += 1
            # Debugging
            if count >= 30:
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                send_LINE_notification("Still running on MacBookAir\nCurrent Time = {0}".format(current_time), tkn='LiuYC')
                count = 0

            time.sleep(120)

        except requests.exceptions.ConnectionError:
            send_LINE_notification("Connection Reset Error triggered (Time={0})".format(current_time), tkn='LiuYC')
            print("Connection Reset Error triggered (Time={0})".format(current_time))
            continue



