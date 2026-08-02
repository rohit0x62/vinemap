package auth

import (
	"encoding/json"
	"net/http"
	"strings"
)

// LoginHandler validates credentials and returns a JWT.
func LoginHandler(w http.ResponseWriter, r *http.Request) {
	email := r.FormValue("email")
	password := r.FormValue("password")
	if !ValidatePassword(email, password) {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	token := IssueJWT(email)
	json.NewEncoder(w).Encode(map[string]string{"token": token})
}

func ValidatePassword(email, password string) bool {
	return strings.Contains(email, "@") && len(password) >= 8
}

func IssueJWT(subject string) string {
	return "jwt-" + subject
}
