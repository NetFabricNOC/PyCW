# This script is bundled only to take advantage of existing source code though it may eventually be used by the primary
# script. Currently just going to use it to take a from board and a to board and migrate all the tickets, eventually
# may extend it with switches that will let me change the functionality slightly, but the goal will always be to effect
# many tickets at once.

import requests
import os

creds = {
    "cwAuth": "Basic bmV0ZmFicmljK25vODRsYVB5R2R6SjEzOEc6M3BFbkRRWWpEN3Q5TWp4cA==",
    "clientID": "d4fafbc9-f049-491d-81e2-6a03f980beab"
}
capi = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0/"


def moveallticketsfromatob(src: str, dest: str) -> None:
    # TODO: get list of all tickets by board
    ticketlist = requests.get(capi + "service/tickets",
                              headers={"Authentication": creds['cwAuth'], "clientID": creds['clientID']},
                              data={"conditions": "board/name=" + src,
                                    "fields": "id,status/name,type/name,subType/name,item"}).text
    # TODO: compile the list of ticket updates
    for ticket in ticketlist:
        result = requests.patch(capi + "service/tickets",
                                headers={"Authentication": creds['cwAuth'], "clientID": creds['clientID']},
                                data=[{"op": "replace", "path": ticket["board"]["name"], "value": dest}])
        os.system("sleep 5s")
        if result.status_code is not 200:
            print("Error: " + result.text)
