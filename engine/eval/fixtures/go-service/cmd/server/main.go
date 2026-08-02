package main

import (
	"encoding/json"
	"net/http"

	"github.com/example/go-fixture/internal/auth"
	"github.com/example/go-fixture/internal/store"
)

func main() {
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/login", auth.LoginHandler)
	http.HandleFunc("/users", store.ListUsersHandler)
	http.ListenAndServe(":8080", nil)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
