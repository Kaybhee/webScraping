import requests
import xlwt
from xlwt import Workbook
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename

url = "https://remoteok.com/api"

def job_postings():
    response = requests.get(url)
    data = response.json()
    return data


def get_data_to_xls(data):
    wb = Workbook()
    job_sheet = wb.add_sheet('Jobs')
    headers = list(data[0].keys())
    for i in range(0, len(headers)):
    
 #Write to an excel file with the rows, column, and column headers
        job_sheet.write(0, i, headers[i])

#Collect the values from the dictionary
   # values = list(data[0].values())
    for i in range(0, len(data)):
        jobs = data[i]
        total_sheet = list(jobs.values())
        for x in range(0, len(total_sheet)):
#Collect the rest of the rows and columns
            job_sheet.write(i + 1, x, total_sheet[x])
    wb.save('remote_jobs')

def send_email(send_from, send_to, subject, text, attachment = None):
    isinstance(send_to, list)
    
    msg = MIMEMultipart()
    msg['from'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime = True)
    msg['subject'] = subject

    msg.attach(MIMEText(text))



    for f in attachment or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(fil.read(), Name = basename(f))
        part['Content-Disposition'] = f'attachment; filename = "{basename(f)}"' 
        msg.attach(part)
    smtp = smtplib.SMTP('smtp.gmail.com: 587')
    smtp.login(send_from, '4745179897')
    smtp.send_mail(send_from, send_to, msg.as_string())
    smtp.close()

if __name__ == "__main__":
    data = job_postings()[1:]
    get_data_to_xls(data)
    send_email('badrukaybhee7@gmail.com', ['abdulkabiropeyemi7@gmail.com'], 'Job postings', 'Kindly find the attached for ur reference', attachment = ['remote_jobs.xlsx'])
