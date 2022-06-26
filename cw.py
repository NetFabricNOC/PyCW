#!/usr/bin/python3

import argparse
import json
import logging
import sys
import null_defs

# region
# init the logger config and parse the args

logging.basicConfig(filename='/var/log/zabbix/cw.log', level="ERROR")
logging.info('processing the parameters into local variables')
logging.debug(f"Dumping the raw cmd: {sys.argv[0:]}")
parsletongue = argparse.ArgumentParser(description='Creates/Updates tickets in connectwise from zabbix')
parsletongue.add_argument('--action', metavar='action', type=str, help="what do you want me to do with this ticket",
                          dest="action")
parsletongue.add_argument('--payload', metavar='payload', type=str,
                          help="json encoded payload from the message body section", dest="payload")
logging.info('setting the common headers for the request')

# init config variables


parseList = parsletongue.parse_args()
logging.debug("Payload is type: %s", type(parseList.payload))
if isinstance(parseList.payload, str):
    data = json.loads(null_defs.sani(parseList.payload))
    logging.debug("data type set to %s after json.loads", type(data))
elif isinstance(parseList.payload, dict):
    data = parseList.payload
else:
    data = []
    logging.critical("payload type is: %s", type(parseList.payload))
logging.debug("dumping the parseList variable:")
logging.debug(parseList)
# endregion

# check for a ticket id and if none found setting to 13 as the default to show its a new ticket
if parseList.action == "create":
    logging.debug("creating the ticket since the action passed from the template was create")
    null_defs.create_ticket(data['event_id'], data['event_sev'], data['host_name'], data['alert_subject'],
                            data['alert_msg'],
                            data['proxy'])

elif parseList.action == "update":
    logging.debug("updating the ticket, since the action passed from the template was update")
    null_defs.update_ticket(null_defs.ticketid_from_problemid(data['event_id']), data['update_msg'])

elif parseList.action == "close":
    logging.debug("closing the ticket, the action passed from the template was close")
    null_defs.update_ticket(null_defs.ticketid_from_problemid(data['event_id']),
                            data['recovery_status'] + " Closing automagically")
    null_defs.close_ticket(null_defs.ticketid_from_problemid(data['event_id']))
    null_defs.remove_ticket(data['event_id'])

else:
    logging.critical("malformed/incorrect action %s, of one of the variables was missing", parseList.action)
