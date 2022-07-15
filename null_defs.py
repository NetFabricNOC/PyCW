import json
import logging
import shelve
from email.mime.multipart import MIMEMultipart

import requests
import yaml
import smtplib


logging.basicConfig(filename='/var/log/zabbix/null_defs.log', level="DEBUG")
logging.debug(commonHeaders)


def add_ticket(problem_id: int, ticket_id: int):
    # TODO: replace hardcoded paths with better relative ones
    # TODO: or even better, ditch this half measure and add tags to the db directly.
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    ticket_map[str(problem_id)] = str(ticket_id)
    ticket_map.sync()
    ticket_map.close()


def remove_ticket(problem_id: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    try:
        ticket_map.pop(str(problem_id))
    except KeyError:
        logging.error("error removing ticket")
    ticket_map.sync()
    ticket_map.close()


def ticketid_from_problemid(problem_id: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    try:
        temp = ticket_map[str(problem_id)]
        ticket_map.close()
        return temp
    except KeyError:
        logging.error("error getting ticketid from problem id: %s", problem_id)





def vimes(error: str, payload: dict):
    # This is called with whatever relevant data when the script fails to create a ticket.
    smtcon = smtplib.SMTP(host='smtp.office365.com', port=25)
    msg = MIMEMultipart()
    msg['From'] = fromYaml['noreply']
    msg['To'] = fromYaml['alert_q']
    msg['Subject'] = "PyCW error: " + error
    msg['Body'] = json.dumps(payload)
    smtcon.sendmail(from_addr=fromYaml['noreply'], to_addrs=fromYaml['alert_q'], msg=f"""Subject: PyCW error: {error}\n\n{json.dumps(payload)}""")
    smtcon.quit()
    return "some such nonsense"







def sani(data: str) -> str:
    return data.replace("\\", "")
