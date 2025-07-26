import os
import requests

def refreshToken(client_id, client_secret, refresh_token, env_path=".env", user_prefix="STRAVA"):
    response = requests.post(
        url="https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )

    if response.status_code != 200:
        raise Exception(f"Failed to refresh token: {response.status_code} - {response.text}")

    tokens = response.json()
    new_access_token = tokens["access_token"]
    new_refresh_token = tokens["refresh_token"]

    print(f"[{user_prefix}] Tokens Refreshed Successfully.")

    with open(env_path, "r") as file:
        lines = file.readlines()

    # Write updated tokens
    with open(env_path, "w") as file:
        for line in lines:
            if line.startswith(f"{user_prefix}_ACCESS_TOKEN="):
                file.write(f"{user_prefix}_ACCESS_TOKEN={new_access_token}\n")
            elif line.startswith(f"{user_prefix}_REFRESH_TOKEN="):
                file.write(f"{user_prefix}_REFRESH_TOKEN={new_refresh_token}\n")
            else:
                file.write(line)

    print(f"[{user_prefix}] Tokens Successfully Updated In .env File.")
