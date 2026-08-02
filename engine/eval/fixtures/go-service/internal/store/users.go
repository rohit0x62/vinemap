package store

import (
	"encoding/json"
	"net/http"
)

type User struct {
	ID    string `json:"id"`
	Email string `json:"email"`
}

var users = []User{
	{ID: "1", Email: "admin@example.com"},
}

func ListUsersHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(users)
}

func GetUserByEmail(email string) *User {
	for _, u := range users {
		if u.Email == email {
			return &u
		}
	}
	return nil
}
