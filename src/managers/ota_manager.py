import json
import machine
import urequests

class OTAManager:

    def __init__(self) -> None:
        pass

    def set_ota_server_endpoint(self, endpoint) -> None:
        self.__endpoint = endpoint

    def download(self) -> list:
        """Download new applications from OTA server

        For example:
            [
                {
                    "path_absolute": <str>,
                    "source": <str>
                }
            ]

        Returns:
            (list) list of dictionaries 
        """
        print('Downloading update ...')
        response = urequests.get(self.__endpoint)
        body = response.text
        json_body = json.loads(body)
        apps = None
        try:
            apps = json_body['app']
        except ValueError as e:
            print("ValueError: %s" % (e))
        except KeyError as e:
            print("KeyError: %s" % (e))
        except Exception as e:
            print("Error: %s" % (e))
        finally:
            return apps

    def update(self, apps) -> None:
        """Update applications in the board
        
        The method writes the new files and applies a soft reboot by means of deep sleep.

        Args:
            apps(list): list of dictionaries in output from the downloads method   
        """
        for app in apps:
            with open(app['path_absolute'], "w") as f:
                f.write(app['source'])
                f.flush()
        
        print('Reboot now ...')
        machine.deepsleep(5000)