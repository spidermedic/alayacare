"""
This program checks alayacare for schedule changes and
sends a text messages when changes are detected.
"""

import sys
import json
import smtplib
import requests
import credentials
from   email.mime.text import MIMEText
from   datetime import datetime, timedelta


def sendmail(message):
    """Sends an email notification regarding changes to the schedule"""
    # Create message object instance
    msg = MIMEText(message)

    # Set message parameters
    password    = credentials.MAIL_PASSWORD
    msg["From"] = credentials.MAIL_SENDER
    msg["To"]   = credentials.MAIL_RECIPIENT
    msg["Subject"] = None

    # Start the server and send a message
    with smtplib.SMTP(host=credentials.SMTP_HOST, port=credentials.SMTP_PORT) as server:
        server.login(msg["From"], password)
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        print("Message sent.\n")


def download_schedule(start_date, end_date):
    """Gets visits for the number of days specified in main()"""

    # Query AlayaCare website for json data
    URL = f"https://{credentials.COMPANY}.alayacare.com/scheduling/admin/getshifts?start={start_date}&end={end_date}&calendar_type=user&employees={credentials.ID}"

    try:
        r = requests.get(URL, auth=(credentials.USERNAME, credentials.PASSWORD))
        return json.loads(r.text)
    except:
        sys.exit("\nUnable download visit data.\n")


def get_city(patientID):
    """Gets the patient's city from a patient api"""

    URL = f"https://nelc.alayacare.com/api/v1/patients/{patientID}"
    try:
        r = requests.get(URL, auth=(credentials.USERNAME, credentials.PASSWORD))
        return json.loads(r.text)["city"]
    except:
        sys.exit("\nUnable download city data.\n")       


def make_new_schedule(downloaded_schedule, days):
    """Creates a multi-day schedule - days is specified in main() - with date keys so that days with no visit are included."""

    new_schedule = {}
    start_date = datetime.now()

    for i in range(days):
        date_str = start_date.strftime("%b %d")
        new_schedule.setdefault(date_str, [])
        start_date += timedelta(days=1)

    for item in downloaded_schedule:
        if item.get("patient") and not item["is_cancelled"]:
            visit = create_visit_from_item(item)
            date = datetime.fromisoformat(item["start"]).strftime("%b %d")
            new_schedule.setdefault(date, []).append(visit)

    # Print the schedule to the console
    print()
    for item in new_schedule:
        print(item)
        if new_schedule[item] == []:
            print("  No Visits Scheduled")
        else:
            for i in new_schedule[item]:
                print(f"  {i[0]}  {i[1]:6} {i[2]:15} {i[3]}")
        print()

    return new_schedule


def create_visit_from_item(item):
    """Creates a visit from an item in the downloaded schedule."""

    patient_id = item["patient"]["id"]
    patient_city = get_city(patient_id)

    # Clean up the service description
    service = item["service"]["name"].split("-")[-1].strip(" ") # Removes the RN- portion
    if service == "":
        service = item["service"]["name"].split("-")[-2].strip(" ") # This is if the service ends with a dash
    service = service.replace("Visit", "") # Removes "Visit" from the string

    start_time = datetime.fromisoformat(item["start"]).strftime("%H:%M")

    return [start_time, patient_id, patient_city, service]


def main():
    
    days = 5
    today = datetime.now().date()
    end_date = today + timedelta(days)

    downloaded_schedule = download_schedule(today, end_date)
    new_schedule = make_new_schedule(downloaded_schedule, days)

    # Open the previous schedule or create it if it doesn't exist
    try:
        with open("saved-schedule.json", "r") as f:
            saved_schedule = json.load(f)
    except:
        with open("saved-schedule.json", "w") as f:
            f.write(json.dumps(new_schedule, indent=4))

    # If the file exists, compare the two schedules
    changes = 0
    message = ""

    for visitDate, new_visits in new_schedule.items():
        try:
            saved_visits = saved_schedule[visitDate]
            if new_visits != saved_visits:
                message += f"\n{visitDate}:\n"

                for new_visit in new_visits:
                    if new_visit not in saved_visits:
                        message += f" (+) {new_visit[3]}, {new_visit[2]}\n"
                        changes += 1

                for saved_visit in saved_visits:
                    if saved_visit not in new_visits:
                        message += f" (-) {saved_visit[3]}, {saved_visit[2]}\n"
                        changes += 1
        except KeyError:
            pass

    # Send an email if changes are found
    if changes > 0:
        print(f"\nFound {changes} changes in the schedule. ", end="")
        sendmail(message)

    # Save the new schedule
    with open("saved-schedule.json", "w") as f:
        f.write(json.dumps(new_schedule, indent=4))


if __name__ == "__main__":
    main()
