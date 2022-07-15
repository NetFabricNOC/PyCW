import logging
import requests
import yaml


class Ticket:

    def __init__(self):
        with open(r'/usr/lib/zabbix/alertscripts/config.yaml') as configFile:
            self.from_yaml = yaml.load(configFile, Loader=yaml.FullLoader)
        self.common_headers = {'Authorization': self.from_yaml['Auth'], 'clientID': self.from_yaml['ClientID'],
                               'content-type': 'application/json', 'Accept': 'application/json'}
        logging.getLogger(__name__)

    def close_ticket(self, ticket_id: int):
        # close the bloody ticket already
        # changing from resolved pending to closed
        composition = """[{"op": "replace", "path": "status", "value": {"name": ">Closed"}}]"""
        try:
            requiem = requests.patch(self.from_yaml['capi'] + "service/tickets/" + str(ticket_id), data=composition,
                                     headers=self.common_headers)
            logging.debug("[%s] Closing response: %s", self.__name__, requiem.text)
        except requests.exceptions.RequestException as e:
            logging.critical("[%s] Closing error: %s", self.__name__, e)
        return "closed ticket"

    def update_ticket(self, ticket_id: int, update: str):
        # todo: if acknowledging ticket set it to work in progress.

        composition = f"""
        {{
            "detailDescriptionFlag": true,
            "text": "{update}",
        }}
        """
        logging.debug("[%s] composition: %s", self.__name__, composition)
        try:
            requiem = requests.post(self.from_yaml['capi'] + "service/tickets/" + str(ticket_id) + "/notes", data=composition,
                                    headers=self.common_headers)
            logging.debug("[%s] request: %s", self.__name__, requiem)
        except requests.exceptions.RequestException as e:
            logging.critical("[%s] Update error: %s", self.__name__, e)

        return "updated the ticket"

    def create_ticket(self, problem_id: int, nsev: int, hostname: str, summary: str, body: str, proxy: str = "default"):
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
        logging.debug("[%s] Found prefix: %s", self.__name__, prefix)

        # Parse the client map from the config file and assign the correct board and company.
        # assigns to the default first, then changes if it finds the prefix.
        # WILL BREAK IF YOU HAVE NO CLIENTS defined

        company = self.from_yaml['Clients'][0]['CustomerID']
        for client in self.from_yaml['Clients']:
            if prefix == client['Prefix']:
                company = client['CustomerID']
                ticket_type = client['Type']
                try:
                    board = client['Board']
                except KeyError:
                    board = self.from_yaml['Board']

        logging.debug("[%s] Setting board and company to: %s %s", self.__name__, board, company)

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
        logging.debug("[%s] url: %s", self.__name__, self.from_yaml['capi'])
        logging.debug("[%s] body: %s", self.__name__, compilation)
        try:
            requiem = requests.post(self.from_yaml['capi'] + "service/tickets",
                                    headers=self.common_headers,
                                    data=compilation)
            logging.debug(requiem.text)
            self.add_ticket(problem_id, requiem.json()["id"])
            logging.debug(requiem)
        except requests.exceptions.RequestException as e:
            logging.critical("[%s] Creation error: %s", self.__name__, e)

        return "created ticket"
