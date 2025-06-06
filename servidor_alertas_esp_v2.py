from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import datetime # Changed from time for more structured timestamping
import os

class ServerConfig:
    LISTEN_ADDRESS = "0.0.0.0"  # Listens on all available network interfaces
    LISTEN_PORT = 8081         # Changed port number, ensure ESP32 matches
    ALERT_ENDPOINT_PATH = "/incoming_alert" # Changed endpoint name

class ESP32NotificationHandler(BaseHTTPRequestHandler):
    def _send_response_message(self, code, content_type, message_bytes):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(message_bytes)

    def do_GET(self):
        url_components = urlparse(self.path)
        request_params = parse_qs(url_components.query)
        timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        if url_components.path == ServerConfig.ALERT_ENDPOINT_PATH:
            event_category = request_params.get("event_type", ["N/A"])[0]
            device_ip = self.client_address[0]
            
            print(f"[{timestamp_str}] EVENT NOTIFICATION from {device_ip}:")
            print(f"  Event Category: {event_category}")
            # Add more details if they are sent by ESP32, e.g.:
            # sensor_val = request_params.get("value", ["N/A"])[0]
            # print(f"  Sensor Value: {sensor_val}")

            self._send_response_message(200, "text/plain", b"Notification successfully logged by server.")
        else:
            print(f"[{timestamp_str}] Denied request for unknown path: {self.path} from {self.client_address[0]}")
            self._send_response_message(404, "text/plain", b"Requested resource not found on this server.")

class CustomAlertHTTPServer:
    def __init__(self, config_obj):
        self.config = config_obj
        self.http_daemon = None

    def display_startup_message(self):
        timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp_str}] Python Alert Server Version 2.0")
        print(f"Initializing server on {self.config.LISTEN_ADDRESS}:{self.config.LISTEN_PORT}")
        print(f"ESP32 should send alerts to this machine's actual IP on the network (e.g., 192.168.1.X) at port {self.config.LISTEN_PORT}.")
        print(f"Expected alert endpoint: {self.config.ALERT_ENDPOINT_PATH}?event_type=some_event")
        print("Press Ctrl+C to terminate the server gracefully.")

    def start_service(self):
        self.display_startup_message()
        try:
            self.http_daemon = HTTPServer(
                (self.config.LISTEN_ADDRESS, self.config.LISTEN_PORT), 
                ESP32NotificationHandler # Using the renamed handler
            )
            self.http_daemon.serve_forever()
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Shutting down server...")
        except OSError as e:
            print(f"ERROR starting server: {e}. Port {self.config.LISTEN_PORT} might be in use.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if self.http_daemon:
                self.http_daemon.server_close()
            timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp_str}] Server has been shut down.")

if __name__ == "__main__":
    # This part is optional, can be useful if script location matters for other files (not in this simple server)
    # current_script_directory = os.path.dirname(os.path.abspath(__file__))
    # print(f"Executing server from directory: {current_script_directory}")
    
    server_settings = ServerConfig()
    alert_service_instance = CustomAlertHTTPServer(server_settings)
    alert_service_instance.start_service() 