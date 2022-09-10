import json
import logging.handlers
import ecs_logging
import shelve
import requests
import yaml
from sendgrid.helpers.mail import Mail

from sendgrid.sendgrid import SendGridAPIClient

with open(r'/usr/lib/zabbix/alertscripts/config.yaml') as configFile:
    fromYaml = yaml.load(configFile, Loader=yaml.FullLoader)
commonHeaders = {'Authorization': fromYaml['Auth'], 'clientID': fromYaml['ClientID'],
                 'content-type': 'application/json', 'Accept': 'application/json'}
loggy = logging.getLogger(__name__)
loggy.setLevel(logging.DEBUG)
handy = logging.handlers.WatchedFileHandler('/var/log/zabbix/null_defs.log')
handy.setFormatter(ecs_logging.StdlibFormatter())
loggy.addHandler(handy)
loggy.debug(commonHeaders)


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
        loggy.error("error removing ticket", extra={"status": "failure", "problem id": problem_id})
    ticket_map.sync()
    ticket_map.close()


def ticketid_from_problemid(problem_id: int):
    ticket_map = shelve.open("/usr/lib/zabbix/alertscripts/tickets.dat")
    try:
        temp = ticket_map[str(problem_id)]
        ticket_map.close()
        return temp
    except KeyError:
        loggy.error("error getting ticketid from problem id",
                    extra={"status": "failure", "problem id": problem_id})


def close_ticket(ticket_id: int):
    # close the bloody ticket already
    # changing from resolved pending to closed
    composition = """[{"op": "replace", "path": "status", "value": {"name": ">Closed"}}]"""
    try:
        requiem = requests.patch(fromYaml['capi'] + "service/tickets/" + str(ticket_id), data=composition,
                                 headers=commonHeaders)
        loggy.debug(f"{requiem.text}", extra={"status": "success", "ticket number": ticket_id})
    except requests.exceptions.RequestException as e:
        loggy.critical(f"{e.response}", extra={"status": "failure", "ticket number": ticket_id})

    return "closed ticket"


def vimes(error: str, payload=None):
    if payload is None:
        payload = []
    msg = Mail(from_email=fromYaml['noreply'], to_emails=fromYaml['alert_q'], subject=f"PyCW Error",
               html_content=f"Error: {error}<br />{json.dumps(payload)}")
    try:
        sendy = SendGridAPIClient(fromYaml['sg_key'])
        respondy = sendy.send(msg)
        loggy.debug(respondy, extra={"status": "success", "type": "debuggy"})
    except Exception as e:
        loggy.debug(e.__str__(), extra={"status": "failure", "type": "error"})
    return "failed successfully"


def update_ticket(ticket_id: int, update: str):
    # add update to the ticket body, if acknowledging ticket set it to work in progress.

    composition = f"""
    {{
        "detailDescriptionFlag": true,
        "text": "{update}",
    }}
    """
    try:
        requiem = requests.post(fromYaml['capi'] + "service/tickets/" + str(ticket_id) + "/notes", data=composition,
                                headers=commonHeaders)
        loggy.debug(requiem.text, extra={"status": "success", "type": "debuggy"})
    except requests.exceptions.RequestException as e:
        loggy.critical(e.response, extra={"status": "failure", "type": "error"})

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

    # Parse the client map from the config file and assign the correct board and company.
    # assigns to the default first, then changes if it finds the prefix.
    # WILL BREAK IF YOU HAVE NO CLIENTS defined
    company = fromYaml['Default_Company']
    ticket_type = fromYaml['Default_Type']
    board = fromYaml['Default_Board']
    ticket_subtype = fromYaml['Default_SubType']
    ticket_item = fromYaml['Default_Item']
    for client in fromYaml['Clients']:
        if prefix == client['Prefix']:
            company = client['CustomerID']
            try:
                ticket_type = client['Type']
            except KeyError:
                pass
            try:
                board = client['Board']
            except KeyError:
                pass
            try:
                ticket_subtype = client['SubType']
            except KeyError:
                pass
            try:
                ticket_item = client['Item']
            except KeyError:
                pass

    # Format all the relevant data into the json request
    compilation = f"""
    {{
        "summary": "{summary[:86]}",
        "type": {{"name": "{ticket_type}"}},
        "subType": {{"name": "{ticket_subtype}"}},
        "item": {{"name": "{ticket_item}"}},
        "recordType": "ServiceTicket",
        "severity": "{severity}",
        "impact": "{impact}",
        "initialDescription": "{body}",
        "board": {{"name": "{board}"}},
        "company": {{"identifier": "{company}"}}
        }}
        """
    loggy.debug(fromYaml['capi'], extra={"variable name": "capi", "type": "debuggy"})
    loggy.debug("".join(f"{key}, {val};" for key, val in json.loads(compilation).items()),
                extra={"type": "debuggy", "variable name": "compilation"})
    try:
        requiem = requests.post(fromYaml['capi'] + "service/tickets", headers=commonHeaders, data=compilation)
        loggy.debug(requiem.text, extra={"type": "debuggy", "result": "success"})
    except requests.exceptions.RequestException as e:
        loggy.critical(e.response, extra={"type": "error", "status": "failure"})
        vimes(e.response, locals())
        return "failed"
    try:
        add_ticket(problem_id, requiem.json()["id"])
    except KeyError as e:
        loggy.critical(e, extra={"type": "error", "status": "failure"})
        vimes(str(e), locals())

    return "created ticket"


def sani(data: str) -> str:
    retval = data.replace('"', "").replace("\\", "")
    return retval.replace("&34", '"')
