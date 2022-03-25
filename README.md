# PyCW
Simple Python CW integration for zabbix

Currently it's a one way function, problems received in zabbix will create a ticket in connectwise and store the ticket number along with teh problem number from zabbix in tickets.dat

I have anonymized the customer information but left teh structure there as an example for how to set that up to handle routing tickets based on proxy prefix. 

That said proxies should be set up in a standardized way, the important part is the prefix, for example customer-hq would be the proxy instaled in customer's hq. If no - is detected the entire string is treated as a prefix so customer, customer-hq, and customer-remote would all be routed the same way.

Logging is done through the python logging module and defaults to /var/log/zabbix/cw.log, this can be changed in teh script but is stored there for ease of finding.
