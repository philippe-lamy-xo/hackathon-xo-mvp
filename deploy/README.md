TPAD Demo Server - systemd unit

To run the demo server as a systemd service on a Linux machine (requires root privileges):

1. Copy the service file to systemd:

   sudo cp tpad-server.service /etc/systemd/system/tpad-server.service

2. Edit the unit to set the correct User and WorkingDirectory if needed.

3. Reload systemd and enable/start the service:

   sudo systemctl daemon-reload
   sudo systemctl enable --now tpad-server.service

4. Check status and logs:

   sudo systemctl status tpad-server.service
   journalctl -u tpad-server.service -f

Note: This is a demo unit intended for local testing only. For production usage, adapt the ExecStart path and user credentials, and consider using a virtualenv or dedicated service user.
