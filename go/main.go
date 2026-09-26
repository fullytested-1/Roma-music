package main

import("encoding/json";"log";"net/http";"os")

func main(){p:=os.Getenv("GO_GATEWAY_PORT");if p==""{p="8080"};http.HandleFunc("/health",func(w http.ResponseWriter,_ *http.Request){w.Header().Set("Content-Type","application/json");json.NewEncoder(w).Encode(map[string]string{"service":"gateway","status":"ok"})});log.Println("Roma gateway :"+p);log.Fatal(http.ListenAndServe(":"+p,nil))}
