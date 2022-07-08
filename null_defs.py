import json
import logging
import shelve
from email.mime.multipart import MIMEMultipart

import requests
import yaml
import smtplib

with open(r'/usr/lib/zabbix/alertscripts/config.yaml') as configFile:
    fromYaml = yaml.load(configFile, Loader=yaml.FullLoader)
commonHeaders = {'Authorization': fromYaml['Auth'], 'clientID': fromYaml['ClientID'],
                 'content-type': 'application/json', 'Accept': 'application/json'}
logging.basicConfig(filename='/var/log/zabbix/null_defs.log', level="DEBUG")
logging.debug(commonHeaders)


def add_ticket(problem_id: int, ticket_id: int):
    # TODO: replace hardcoded paths with better relative ones
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


def close_ticket(ticket_id: int):
    # close the bloody ticket already
    # changing from resolved pending to closed
    composition = """[{"op": "replace", "path": "status", "value": {"name": ">Closed"}}]"""
    try:
        requiem = requests.patch(fromYaml['capi'] + "service/tickets/" + str(ticket_id), data=composition, headers=commonHeaders)
        logging.debug("Closing response: %s", requiem.text)
    except requests.exceptions.RequestException as e:
        logging.critical("Closing error: %s", e)

    return "closed ticket"


def vimes(error: str, payload: dict):
    # This is called with whatever relevant data when the script fails to create a ticket.
    smtcon = smtplib.SMTP(host='smtp.office365.com', port=25)
    msg = MIMEMultipart()
    msg['From'] = fromYaml['noreply']
    msg['To'] = fromYaml['alert_queue']
    msg['Subject'] = "PyCW error: " + error
    msg['Body'] = json.dumps(payload)
    smtcon.sendmail(from_addr=fromYaml['noreply'], to_addrs=fromYaml['alert_q'], msg=f"""Subject: PyCW error: {error}\n\n{json.dumps(payload)}""")
    smtcon.quit()
    return "some such nonsense"


def update_ticket(ticket_id: int, update: str):
    # add update to the ticket body, if acknowledging ticket set it to work in progress.

    composition = f"""
    {{
        "detailDescriptionFlag": true,
        "text": "{update}",
    }}
    """
    logging.debug(composition)
    try:
        requiem = requests.post(fromYaml['capi'] + "service/tickets/" + str(ticket_id) + "/notes", data=composition,
                                headers=commonHeaders)
        logging.debug(requiem)
    except requests.exceptions.RequestException as e:
        logging.critical("Update error: %s", e)

    return "updated the ticket"


def create_ticket(problem_id: int, nsev: int, hostname: str, summary: str, body: str, proxy: str = "default"):
    # The zabbix severity to connectwise sev/impact mapping, these values can
    # be changed if needed, I attempted to set them to sane defaults.
    if nsev <= 2:
        severity = "Low"
        impact = "Low"
    elif nsev == 3:
        severity = "Medium"
        impact = "Medium"
    elif nsev >= 4:
        severity = "High"
        impact = "High"
    else:
        severity = "Medium"
        impact = "High"
    # This bit splits the proxy on - to get the prefix for the customer.
    # used to group multiple proxies to the same company/board
    if proxy.find('-') != -1:
        prefix = proxy.split('-')[0]
    else:
        prefix = proxy
    logging.debug("Found prefix: %s", prefix)

    # Parse the client map from the config file and assign the correct board and company.
    # assigns to the default first, then changes if it finds the prefix.
    # WILL BREAK IF YOU HAVE NO CLIENTS defined
    ticket_type = ""
    company = fromYaml['Clients'][0]['CustomerID']
    for client in fromYaml['Clients']:
        if prefix == client['Prefix']:
            company = client['CustomerID']
            ticket_type = client['Type']
            try:
                board = client['Board']
            except KeyError:
                board = fromYaml['Board']

    logging.debug("Setting board and company to: %s %s", board, company)

    # Format all the relevant data into the json request
    compilation = f"""
    {{
        "summary": "{summary}",
        "type": {{"name": "{ticket_type}"}},
        "recordType": "ServiceTicket",
        "severity": "{severity}",
        "impact": "{impact}",
        "initialDescription": "{body}",
        "board": {{"name": "{board}"}},
        "company": {{"identifier": "{company}"}}
        }}
        """
    logging.debug("url: " + fromYaml['capi'])
    logging.debug("body: " + compilation)
    try:
        requiem = requests.post(fromYaml['capi'] + "service/tickets", headers=commonHeaders, data=compilation)
        logging.debug(requiem.text)
        add_ticket(problem_id, requiem.json()["id"])
        logging.debug(requiem)
    except requests.exceptions.RequestException as e:
        logging.critical("Creation error: %s", e)

    return "created ticket"


def sani(data: str) -> str:
    return data.replace("\\", "")
