# VPN
This was a project I completed in Spring 2025 for my Computer Networking class. The purpose of this project was to design an application that would show our knowledge of socket programming and various concepts within Computer Networking. The concepts used here are: Client/Server Communication, Process to Process Communication, Network Edge Monitoring (used Wireshark), and some elements of Network Security.

There are 2 files, client.py and server.py. 
  The client is designed to have the user select which server they want to connect to through the use of buttons. It will then communicate to Windows to tell the OS to   connect to the selected server via proxy settings. **This client will only work on Windows devices**
  
  The server sets up bidirectional communication between your client and the remote server (any outgoing requests). It is mainly designed to handle HTTP/S requests and   other applications may have issues.
