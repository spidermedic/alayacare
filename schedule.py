#!/usr/bin/env python

import sys
import json
import smtplib
import requests
import credentials
from email.mime.text import MIMEText
from datetime import datetime, timedelta


def sendmail(message):

    # create message object instance
    msg = MIMEText(message)

    # set message parameters
    password = credentials.PASSWORD
    msg["From"] = credentials.SENDER
    msg["Subject"] = None

    msg["To"] = credentials.RECIPIENT

    # start server and send message
    with smtplib.SMTP(host=credentials.SMTP_HOST, port=credentials.SMTP_PORT) as server:
        server.login(msg["From"], password)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        print("Message sent.\n")


def get_schedule(start_date, end_date):

    # Query AlayaCare website for json data
    URL = f"https://{credentials.COMPANY}.alayacare.com/scheduling/admin/getshifts?start={start_date}&end={end_date}&calendar_type=user&employees={credentials.ID}"

    try:
        r = requests.get(URL, auth=(credentials.USERNAME, credentials.PASSWORD))
        return json.loads(r.text)
    except:
        sys.exit("\nUnable to get data from website\n")


def make_new_schedule(downloaded_schedule):
    # creates a 4 day schedule with date keys  so that days with no visit are included.
    new_schedule = {}
    n = datetime.now()

    # create the dictionary keys using the date
    new_schedule[n.strftime("%b %d")] = []
    for i in range(3):
        n += timedelta(days=1)
        new_schedule[n.strftime("%b %d")] = []

    # add the downloaded visits to the new schedule
    for item in downloaded_schedule:
        this_visit = datetime.fromisoformat(item["start"])
        if item.get("patient") and not item["is_cancelled"]:
            patient = item["patient"]["name"]
            service = item["service"]["name"].split("-")[-1]
            date = this_visit.strftime("%b %d")
            visit = [this_visit.strftime("%H:%M"), patient, service]
            new_schedule[date].append(visit)

    # print the schedule to the console
    print()
    for item in new_schedule:
        print(item)
        if new_schedule[item] == []:
            print("  No Visits Scheduled")
        else:
            for i in new_schedule[item]:
                print(f"  {i[0]}  {i[1]:22}  {i[2]}")
        print()

    return new_schedule


def main():

    today = datetime.now().date()
    end_date = today + timedelta(days=4)

    downloaded_schedule = get_schedule(today, end_date)
    new_schedule = make_new_schedule(downloaded_schedule)

    # open the previous schedule or create it if it doesn't exist
    try:
        with open("schedule.json", "r") as f:
            previous_schedule = json.load(f)
    except:
        with open("schedule.json", "w") as f:
            f.write(json.dumps(new_schedule, indent=4))

    # if the file exists, compare the schedules
    changes = 0
    # message = f"{datetime.now().strftime('%m/%d/%Y %H:%M')}\nSchedule updated: \n"
    message = ""

    for item in new_schedule:

        try:
            total_visits = len(new_schedule[item]) - len(previous_schedule[item])

            if total_visits > 0:
                message += f" {item} - Visit added\n"
                changes += 1
            elif total_visits < 0:
                message += f" {item} - Visit removed\n"
                changes += 1
            else:
                pass
        except:
            pass

    if changes > 0:

        print(f"\nFound {changes} changes in the schedule. ", end="")
        sendmail(message)

        # save the new schedule
    with open("schedule.json", "w") as f:
        f.write(json.dumps(new_schedule, indent=4))


if __name__ == "__main__":
    main()
