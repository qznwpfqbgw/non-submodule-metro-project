# QUIC_Upload

### Server
```
$ go run ./server/server_upload.go
```
Parameters:  
- `-h`: host  
- `-p`: port  
- `-d`: path to store receiving files  
- `-ld`: path to store log files  

### Client
```
$ go run ./client/client_upload.go
```
Parameters:  
- `-h`: host  
- `-p`: port  
- `-f`: transfering file  
- `i`: interface to bind
- `-ld`: path to store log files  

### qlog Key Modification
- https://hackmd.io/@KilliMilli/ry36Ne9fR

### Note
- To get the latest quic-go version: `go get -u github.com/mollyy0514/quic-go`