# This program checks alayacare for schedule changes and
# sends a text messages when changes are detected.

import sys
import json
import smtplib
import requests
import credentials
from   email.mime.text import MIMEText
from   datetime import datetime, timedelta


def sendmail(message):

    # create message object instance
    msg = MIMEText(message)

    # set message parameters
    password    = credentials.MAIL_PASSWORD
    msg["From"] = credentials.MAIL_SENDER
    msg["To"]   = credentials.MAIL_RECIPIENT
    msg["Subject"] = None


    # start server and send message
    with smtplib.SMTP(host=credentials.SMTP_HOST, port=credentials.SMTP_PORT) as server:
        server.login(msg["From"], password)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        print("Message sent.\n")


# Query Alayacare and get visits for the number of days specified in main() 
def download_schedule(start_date, end_date):

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
            patient = item["patient"]["name"].split(" ")[-1] # Extracts last name
            patientID = item["patient"]["id"]
            service = item["service"]["name"].split("-")[-1] # Removes the RN- portion
            if service == "":
                service = item["service"]["name"].split("-")[-2] # This is if the service ends with a dash
            date = this_visit.strftime("%b %d")
            visit = [this_visit.strftime("%H:%M"), patientID, patient, service]
            new_schedule[date].append(visit)


    # print the schedule to the console
    print()
    for item in new_schedule:
        print(item)
        if new_schedule[item] == []:
            print("  No Visits Scheduled")
        else:
            for i in new_schedule[item]:
                print(f"  {i[0]}  {i[1]:6} {i[2]:15}  {i[3]}")
        print()

    return new_schedule


def main():

    today = datetime.now().date()
    end_date = today + timedelta(days=4)

    downloaded_schedule = download_schedule(today, end_date)
    new_schedule = make_new_schedule(downloaded_schedule)

    # open the previous schedule or create it if it doesn't exist
    try:
        with open("saved-schedule.json", "r") as f:
            saved_schedule = json.load(f)
    except:
        with open("saved-schedule.json", "w") as f:
            f.write(json.dumps(new_schedule, indent=4))

    # if the file exists, compare the schedules
    changes = 0
    message = ""

    for item in new_schedule:
        try:
            total_visits = len(new_schedule[item]) - len(saved_schedule[item])

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
    with open("saved-schedule.json", "w") as f:
        f.write(json.dumps(new_schedule, indent=4))


if __name__ == "__main__":
    main()
