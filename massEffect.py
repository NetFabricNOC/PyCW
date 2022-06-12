# This script is bundled only to take advantage of existing source code though it may eventually be used by the primary
# script. Currently just going to use it to take a from board and a to board b and migrate all the tickets, eventually
# may extend it with switches that will let me change the functionality slightly, but the goal will always be to effect
# many tickets at once.
import argparse
import json
import os
import sys

import requests

creds = {
    "cwAuth": "Basic bmV0ZmFicmljK25vODRsYVB5R2R6SjEzOEc6M3BFbkRRWWpEN3Q5TWp4cA==",
    "clientID": "d4fafbc9-f049-491d-81e2-6a03f980beab"
}
capi = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0/"
Headers = {'Authorization': creds['cwAuth'], 'clientID': creds['clientID'],
           'content-type': 'application/json', 'Accept': 'application/json'}
parsletongue = argparse.ArgumentParser(description='Effects massive change in the connectwise environment')
parsletongue.add_argument('--action', type=str, required=True)
parsletongue.add_argument('--src', type=str)
parsletongue.add_argument('--dest', type=str)
argenvastholt = parsletongue.parse_args()


def list_boards() -> list:
    print("listing boards")
    return json.loads(requests.get(capi + "service/boards?fields=id,name&pagesize=1000", headers=Headers).text)


def board_id_from_name(board_name: str) -> int:
    print("getting board id for board named: " + board_name)
    for board in list_boards():
        if board["name"] == board_name:
            print("Found board id " + str(board["id"]))
            return board["id"]

    print("unable to find board id")
    sys.exit()


def return_first_team_id_for_board(board_id: int) -> int:
    print("getting team id for board: " + str(board_id))
    return json.loads(requests.get(capi + "service/boards/" + str(board_id) + "/teams?fields=id,name",
                                   headers=Headers).text)[0]["id"]


def get_full_list_of_tickets_from(board: str, retval: list = [], page: int = 1) -> list:
    print("getting page: " + str(page))
    result = json.loads(requests.get(capi +
                                     "service/tickets?conditions=board/name=\"" + board +
                                     "\"&fields=id,status/name,type/name,subType/name,item,company/name&pagesize=1000&page=" +
                                     str(page),
                                     headers=Headers).text)
    print("found " + str(len(result)) + " tickets on this page")
    retval.extend(result)
    print("found " + str(len(retval)) + " tickets total so far")
    if len(result) < 1000:
        print("less than 1k tickets on this page, exiting")
        return retval
    else:
        print("1k tickets found, going another level deeper")
        return get_full_list_of_tickets_from(board, retval, page + 1)


def move_all_tickets_from_a_to_b(src: str, dest: str) -> None:
    print("getting the team id")
    board_id = board_id_from_name(dest)
    mapping = get_type_map_for_board(board_id)
    team_id = return_first_team_id_for_board(board_id)
    print("found team id: " + str(team_id))
    for ticket in get_full_list_of_tickets_from(src):
        print("Processing ticket: " + json.dumps(ticket))
        result = requests.patch(capi + "service/tickets/" + str(ticket["id"]),
                                headers=Headers,
                                data=json.dumps([{"op": "replace",
                                                  "path": "board",
                                                  "value": {"name": dest}},
                                                 {"op": "replace",
                                                  "path": "status",
                                                  "value": {"name": ticket["status"]["name"]}},
                                                 {"op": "replace",
                                                  "path": "type",
                                                  "value": {"name": mapping["company"]["name"]}},
                                                 {"op": "replace",
                                                  "path": "subType",
                                                  "value": {"name": mapping["subType"]["name"]}},
                                                 {"op": "replace",
                                                  "path": "item",
                                                  "value": {"name": mapping["item"]["name"]}},
                                                 {"op": "replace",
                                                  "path": "team",
                                                  "value": {"id": team_id}}]))
        os.system("sleep 5s")
        if result.status_code != 200:
            print("Error: " + result.text)


def get_type_map_for_board(board_id: int) -> dict:
    print("getting map")
    associations = json.loads(
        requests.get(capi + "service/boards/" + str(board_id) + "/typeSubTypeItemAssociations", headers=Headers).text)
    print("getting type list")
    types = json.loads(requests.get(capi + "service/boards/" + str(board_id) + "/types?fields=id,name,inactiveFlag",
                                    headers=Headers).text)
    print("getting sub type list")
    sub_types = json.loads(
        requests.get(capi + "service/boards/" + str(board_id) + "/subTypes?fields=id,name,inactiveFlag",
                     headers=Headers).text)
    # print(json.dumps(sub_types))
    print("getting item list")
    items = json.loads(
        requests.get(capi + "service/boards/" + str(board_id) + "/items?fields=id,name,inactiveFlag",
                     headers=Headers).text)
    print(json.dumps(items))
    print("looping through associations")
    for assoc in associations:
        print("testing association: " + str(assoc))
        print("looping through board types")
        for board_type in types:
            print("testing if board type id (" + str(board_type["id"]) + ") matches association type id (" + str(
                assoc["type"][
                    "id"]) + ") and that the inactive flag is not true (" + str(board_type["inactiveFlag"]) + ")")
            if (board_type["id"] == assoc["type"]["id"]) and (not board_type["inactiveFlag"]) and ("subType" in assoc):
                print("found active type, searching through sub types")
                for sub_type in sub_types:
                    print("testing if sub type id (" +
                          str(sub_type["id"]) +
                          ") matches association sub type id (" +
                          str(assoc["subType"]["id"]) +
                          ") and that the inactive flag is not true (" +
                          str(sub_type["inactiveFlag"]) +
                          ")")
                    if (sub_type["id"] == assoc["subType"]["id"]) and (not sub_type["inactiveFlag"]) and ("item" in assoc):
                        print("found active subtype")
                        for item in items:
                            print("testing if item id (" +
                                  str(item["id"]) +
                                  ") matches association item id (" +
                                  str(assoc["item"]["id"]) +
                                  ") and that the inactive flag is not true (" +
                                  str(item["inactiveFlag"]) +
                                  ")")
                            if (item["id"] == assoc["item"]["id"]) and (not item["inactiveFlag"]):
                                print("found active item")
                                return {"type": {"id": assoc["type"]["id"], "name": assoc["type"]["name"]},
                                        "sub_type": {"id": assoc["subType"]["id"], "name": assoc["subType"]["name"]},
                                        "item": {"id": assoc["item"]["id"], "name": assoc["item"]["name"]}}
    return {"type": {"id": 0, "name": ""},
            "sub_type": {"id": 0, "name": ""},
            "item": {"id": 0, "name": ""}}


if argenvastholt.action == "migrate":
    print("Source board: " + argenvastholt.src)
    print("Destination board: " + argenvastholt.dest)
    move_all_tickets_from_a_to_b(argenvastholt.src, argenvastholt.dest)
