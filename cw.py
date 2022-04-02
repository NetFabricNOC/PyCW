#!/usr/bin/python3

import sys, requests, logging, argparse, json, shelve, yaml

# region
# init the logger config and parse the args
with open(r'/usr/lib/zabbix/alertscripts/config.yaml') as configFile:
    fromYaml = yaml.load(configFile, Loader=yaml.FullLoader)

logging.basicConfig(filename='/var/log/zabbix/cw.log', level=fromYaml['logLevel'])
logging.info('processing the parameters into local variables')
logging.debug(f"Dumping the raw cmd: {sys.argv[0:]}")
parsletongue = argparse.ArgumentParser(description='Creates/Updates tickets in connectwise from zabbix')
parsletongue.add_argument('--action', metavar=('action'), type=str, help="what do you want me to do with this ticket", dest="action")
parsletongue.add_argument('--payload', metavar=('payload'), type=str, help="json encoded payload from the message body section", dest="payload")
logging.info('setting the common headers for the request')

# init config variables

commonHeaders = f"""{{"Authorization": '{fromYaml['Auth']}', "clientID": '{fromYaml['ClientID']}', "content-type": "application/json", "Accept": "application/json"}}"""
baseURL = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0/"
logging.debug(commonHeaders)
parseList = parsletongue.parse_args()
data = json.loads(parseList.payload)
logging.debug("dumping the parseList variable:")
logging.debug(parseList)
# endregion

# misc and sundry function definition
## TODO: make this whole block obsolete, tag the problems with the connectwise ticket numbers and add callback functions to connectwise
def add_ticket(problemID: int, ticketID: int):
    ## TODO: replace hardcoded paths with better relative ones
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
    try:
        requiem = requests.patch(baseURL + "service/tickets/" + str(ticketID), data=composition, headers=commonHeaders)
    except requests.exceptions.RequestException as e:
        logging.critical("Closing error: %s", e)
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
    try:
        requiem = requests.post(baseURL + "service/tickets/" + str(ticketID) + "/notes", data=composition, headers=commonHeaders)
    except requests.exceptions.RequestException as e:
        logging.critical("Update error: %s", e)
    logging.debug(requiem)

    return "updated the ticket"

def createTicket(nsev: int, summary: str, body: str, proxy: str = "default"):
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
    board = fromYaml['Clients'][0]['Board']
    company = fromYaml['Clients'][0]['CustomerID']
    for client in fromYaml['Clients']:
        if prefix == client['Prefix']:
            board = client['Board']
            company = client['CustomerID']

    logging.debug("Setting board and company to: %s %s", board, company)

    # Format all the relevant data into the json request
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
    try:
        requiem = requests.post(baseURL + "service/tickets", headers=commonHeaders, data=compilation)
    except requests.exceptions.RequestException as e:
        logging.critical("Creation error: %s", e)
    logging.debug(requiem.text)
    add_ticket(data['event_id'], requiem.json()["id"])
    logging.debug(requiem)

    return "created ticket"

def fail(msg: str):
    logging.error("wierd stuff is happening, haaaaaalp. " + msg)

def chkVar(value: str):
    if type(value) != int:
        if value[:1:] != '{':
            return True

def sani(data: str):
    return data.replace("\"", "").replace("\\","")
# body stuffs, routing the requests

# check for a ticket id and if none found setting to 13 as the default to show its a new ticket
if parseList.action == "create":
    logging.debug("creating the ticket since the action passed from the template was create")
    createTicket(data['event_sev'], sani(data['alert_subject']), sani(data['alert_msg']), data['proxy'])

elif parseList.action == "update":
    logging.debug("updating the ticket, since the action passed from the template was update")
    updateTicket(ticketid_from_problemid(data['event_id']), sani(data['update_msg']))

elif parseList.action == "close":
    logging.debug("closing the ticket, the action passed from the template was close")
    updateTicket(ticketid_from_problemid(data['event_id']), sani(data['recovery_status']) + " Closing automagically")
    closeTicket(ticketid_from_problemid(data['event_id']))
    remove_ticket(data['event_id'])

else:
    fail(f'malformed/incorrect action {parseList.action}, of one of the variables was missing')
