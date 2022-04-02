#!/usr/bin/python3

import sys, requests, logging, argparse, json, shelve, yaml, null_defs

# region
# init the logger config and parse the args
with open(r'/usr/lib/zabbix/alertscripts/config.yaml') as configFile:
    fromYaml = yaml.load(configFile, Loader=yaml.FullLoader)

logging.basicConfig(filename='/var/log/zabbix/cw.log', level=fromYaml['logLevel'].upper())
logging.info('processing the parameters into local variables')
logging.debug(f"Dumping the raw cmd: {sys.argv[0:]}")
parsletongue = argparse.ArgumentParser(description='Creates/Updates tickets in connectwise from zabbix')
parsletongue.add_argument('--action', metavar=('action'), type=str, help="what do you want me to do with this ticket", dest="action")
parsletongue.add_argument('--payload', metavar=('payload'), type=str, help="json encoded payload from the message body section", dest="payload")
logging.info('setting the common headers for the request')

# init config variables

commonHeaders = {'Authorization': fromYaml['Auth'], 'clientID': fromYaml['ClientID'], 'content-type': 'application/json', 'Accept': 'application/json'}
baseURL = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0/"
logging.debug(commonHeaders)
parseList = parsletongue.parse_args()
logging.debug("Payload is type: %s", type(parseList.payload))
if isinstance(parseList.payload, str):
    data = json.loads(sani(parseList.payload))
    logging.debug("data type set to %s after json.loads", type(data))
elif isinstance(parseList.payload, dict):
    data = parseList.payload
else:
    logging.critical("payload type is: %s", type(parseList.payload)
logging.debug("dumping the parseList variable:")
logging.debug(parseList)
# endregion

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
