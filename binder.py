from xmlrpc.server import SimpleXMLRPCServer
import datetime
import logging

logger = logging.getLogger(__name__)
procedures = {}
host = "localhost"
port = 65431

def register_procedure(procedure_name, address, port):
    global procedures
    procedures[procedure_name] = f"{address}:{port}"
    return True

def lookup_procedure(procedure_name):
    global procedures
    return procedures[procedure_name]

def main():
    logging.basicConfig(filename='binder.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")
    try:
        with SimpleXMLRPCServer((host, port)) as server:
            server.register_introspection_functions()
            server.register_function(register_procedure)
            server.register_function(lookup_procedure)
            try:
                server.serve_forever()
            except KeyboardInterrupt as e: 
                logger.error(f"{datetime.datetime.now()} at {main.__name__} serve_forever call", exc_info=e)
                exit()
            except Exception as e:
                logger.error(f"{datetime.datetime.now()} at {main.__name__} serve_forever call", exc_info=e)
                exit()
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__} server", exc_info=e)
        exit()
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    main()
    