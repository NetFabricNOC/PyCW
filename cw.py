#!/usr/bin/python3

import sys, requests, logging, argparse, json, shelve

# region
# init the logger config and parse the args

logging.basicConfig(filename='/var/log/zabbix/cw.log', level=logging.ERROR)
logging.info('processing the parameters into local variables')
logging.debug(f"Dumping the raw cmd: {sys.argv[0:]}")
parsletongue = argparse.ArgumentParser(description='Creates/Updates tickets in connectwise from zabbix')
parsletongue.add_argument('--action', metavar=('action'), type=str, help="dafuq you want me to do with this ticket", dest="action")
parsletongue.add_argument('--payload', metavar=('payload'), type=str, help="json encoded payload from the message body section", dest="payload")
logging.info('setting the common headers for the request')

# init config variables

authID = ""
clientID = ""
commonHeaders = {"Authorization": 'Basic  ', "clientID": '', "content-type": "application/json", "Accept": "application/json"}
baseURL = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0/"
logging.debug(commonHeaders)
parseList = parsletongue.parse_args()
data = json.loads(parseList.payload)
logging.debug("dumping the parseList variable:")
logging.debug(parseList)
# endregion

# misc and sundry function definition

def add_ticket(problemID: int, ticketID: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    ticket_map[str(problemID)] = str(ticketID)
    ticket_map.sync()
    ticket_map.close()
def remove_ticket(problemID: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    ticket_map.pop(str(problemID))
    ticket_map.sync()
    ticket_map.close()
def ticketid_from_problemid(problemID: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    temp = ticket_map[str(problemID)]
    ticket_map.close()
    return temp

def closeTicket(ticketID: int):

    # close the bloody ticket already

    composition = """[{"op": "replace", "path": "status", "value": {"name": "Resolved Pending 24 Hrs"}}]"""
    requiem = requests.patch(baseURL + "service/tickets/" + str(ticketID), data=composition, headers=commonHeaders)
    logging.debug("Closing response: %s", requiem.text)
    return "closed ticket"

def updateTicket(ticketID: int, update: str):

    # add update to the ticket body, if acknowledging ticket set it to work in progress.

    composition = f"""
    {{
        "detailDescriptionFlag": true,
        "text": "{update}",
    }}
    """
    logging.debug(composition)
    requiem = requests.post(baseURL + "service/tickets/" + str(ticketID) + "/notes", data=composition, headers=commonHeaders)
    logging.debug(requiem)

    return "updated the ticket"

def createTicket(nsev: int, summary: str, body: str, proxy: str):
    board, company = "", ''
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
    if proxy.find('-') != -1:
        prefix = proxy.split('-')[0]
    else:
        prefix = proxy
    logging.debug("Found prefix: %s", prefix)
    if prefix == "customer":
        board = "noc board"
        company = "customer"
    elif prefix == "other_customer":
        board = "helpdesk board"
        company = "other_customer"
    else:
        board = "default board"
        company = "msp"
    logging.debug("Setting board and company to: %s %s", board, company)
    compilation = f"""
    {{
        "summary": "{summary}", 
        "recordType": "ServiceTicket", 
        "severity": "{severity}", 
        "impact": "{impact}", 
        "initialDescription": "{body}", 
        "board": {{"name": "{board}"}}, 
        "company": {{"identifier": "{company}"}}
        }}
        """
    logging.debug("url: " + baseURL)
    logging.debug("body: " + compilation)
    requiem = requests.post(baseURL + "service/tickets", headers=commonHeaders, data=compilation)
    logging.debug(requiem.text)
    add_ticket(data['event_id'], requiem.json()["id"])
    logging.debug(requiem)

    return "created ticket"

def fail(msg: str):
    logging.error("wierd shit is happening, haaaaaalp. " + msg)

def chkVar(value: str):
    if type(value) != int:
        if value[:1:] != '{':
            return True

# body stuffs, routing the requests

# check for a ticket id and if none found setting to 13 as the default to show its a new ticket
if parseList.action == "create":
    logging.debug("creating the ticket since the action passed from the template was create")
    createTicket(data['event_sev'], data['alert_subject'], data['alert_msg'], data['proxy'])

elif parseList.action == "update":
    logging.debug("updating the ticket, since the action passed from the template was update")
    updateTicket(ticketid_from_problemid(data['event_id']), data['update_msg'])

elif parseList.action == "close":
    logging.debug("closing the ticket, the action passed from the template was close")
    updateTicket(ticketid_from_problemid(data['event_id']), data['recovery_status'] + " Closing automagically")
    closeTicket(ticketid_from_problemid(data['event_id']))
    remove_ticket(data['event_id'])

else:
    fail(f'malformed/incorrect action {parseList.action}, of one of the variables was missing')
