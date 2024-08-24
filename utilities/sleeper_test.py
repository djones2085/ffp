import requests

# Function to fetch data from Sleeper API
def fetch_data_from_sleeper():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        # Filter the data to include only team defenses (DST)
        dst_data = [player_info for player_info in data.values() if 'position' in player_info and player_info['position'] == 'DEF']
        
        return dst_data
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")

# Fetch DST data and print the format of the first one
def main():
    try:
        dst_data = fetch_data_from_sleeper()
        if dst_data:
            print("Format of the first Defense and Special Teams (DST) player info:")
            print(dst_data[0])  # Print the full dictionary for the first DST entry
        else:
            print("No DST data found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
