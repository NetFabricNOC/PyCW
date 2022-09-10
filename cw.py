#!/usr/bin/python3

import argparse
import json
import logging.handlers
import sys
import ecs_logging

import null_defs

loggy_cwpy = logging.getLogger(__name__)
loggy_cwpy.setLevel(logging.ERROR)
handy = logging.handlers.WatchedFileHandler('/var/log/zabbix/pycw.log')
handy.setFormatter(ecs_logging.StdlibFormatter())
loggy_cwpy.addHandler(handy)
loggy_cwpy.info('processing the parameters into local variables')
loggy_cwpy.debug(f"Dumping the raw cmd: {sys.argv[0:]}")
parsletongue = argparse.ArgumentParser(description='Creates/Updates tickets in connectwise from zabbix')
parsletongue.add_argument('--action', metavar='action', type=str, help="what do you want me to do with this ticket",
                          dest="action")
parsletongue.add_argument('--payload', metavar='payload', type=str,
                          help="json encoded payload from the message body section", dest="payload")

# init config variables
parseList = parsletongue.parse_args()
loggy_cwpy.debug("Payload is type: %s", type(parseList.payload))
loggy_cwpy.debug("Payload: %s", parseList.payload)
if isinstance(parseList.payload, str):
    data = json.loads(null_defs.sani(parseList.payload))
    loggy_cwpy.debug("data type set to %s after json.loads", type(data))
elif isinstance(parseList.payload, dict):
    data = parseList.payload
else:
    data = []
    loggy_cwpy.critical("payload type is: %s", type(parseList.payload))
# endregion

# check for a ticket id and if none found setting to 13 as the default to show it's a new ticket
if parseList.action == "create":
    loggy_cwpy.debug("creating the ticket since the action passed from the template was create")
    try:
        null_defs.create_ticket(data['event_id'], data['event_sev'], data['host_name'], data['alert_subject'],
                                data['alert_msg'],
                                data['proxy'])
    except Exception as err:  # pylint: disable=broad-except
        loggy_cwpy.error("Ticket creation error: %s. Locals: %s", err,
                         "".join(f"{key}, {val};" for key, val in locals()))
        null_defs.vimes(err.__str__(), data)
    # add other exceptions as they are found for proper handling.

elif parseList.action == "update":
    loggy_cwpy.debug("updating the ticket, since the action passed from the template was update")
    null_defs.update_ticket(null_defs.ticketid_from_problemid(data['event_id']), data['update_msg'])

elif parseList.action == "close":
    loggy_cwpy.debug("closing the ticket, the action passed from the template was close")
    null_defs.update_ticket(null_defs.ticketid_from_problemid(data['event_id']),
                            data['recovery_status'] + " Closing automagically")
    null_defs.close_ticket(null_defs.ticketid_from_problemid(data['event_id']))
    null_defs.remove_ticket(data['event_id'])

else:
    loggy_cwpy.critical("malformed/incorrect action %s, of one of the variables was missing", parseList.action)
